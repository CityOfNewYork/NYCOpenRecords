"""
.. module:: auth.views.

   :synopsis: Authentication utilities for NYC OpenRecords

"""
import ssl
import hmac
import requests

from json import dumps
from hashlib import sha1
from base64 import b64encode
from requests.exceptions import SSLError
from urllib.parse import urljoin, urlparse

from flask import (
    current_app,
    session,
    url_for,
    request,
    abort,
    redirect,
)
from flask_login import login_user, current_user
from app import (
    login_manager
)
from app.models import Users, AgencyUsers, Events
from app.constants import user_type_auth, USER_ID_DELIMITER
from app.constants.web_services import (
    USER_ENDPOINT,
    EMAIL_VALIDATION_ENDPOINT,
    EMAIL_VALIDATION_STATUS_ENDPOINT,
    TOU_ENDPOINT,
    TOU_STATUS_ENDPOINT,
    ENROLLMENT_ENDPOINT,
    ENROLLMENT_STATUS_ENDPOINT,
)
from app.auth.constants import error_msg
from app.lib.db_utils import create_object, update_object
from app.lib.user_information import create_mailing_address
from app.lib.redis_utils import (
    redis_get_user_session,
    redis_delete_user_session
)

from ldap3 import Server, Tls, Connection


@login_manager.user_loader
def user_loader(user_id):
    """
    Given a user_id (GUID + UserType), return the associated User object.

    :param unicode user_id: user_id (GUID + UserType) of user to retrieve
    :return: User object
    """
    user_id = user_id.split(USER_ID_DELIMITER)
    return Users.query.filter_by(guid=user_id[0], auth_user_type=user_id[1]).first()


def destroy_session(user_id):
    """
    Destroy a backend user session and return boolean value (True for successful destroy).

    :param session_id: Backend KVSession ID (session.sid_s)
    :type session_id: String
    :return: Boolean
    """
    user = Users.query.filter_by(guid=user_id[0], auth_user_type=user_id[1]).first()
    session_id = user.session_id
    user_session = redis_get_user_session(session_id)

    if user.auth_user_type == user_type_auth.AGENCY_USER:
        revoke_and_remove_access_token(user_session)

    redis_delete_user_session(session_id)


def update_openrecords_user(form):
    """
    Update OpenRecords-specific user attributes.
    :param form: validated ManageUserAccountForm or ManageAgencyUserAccountForm
    :type form: app.auth.forms.ManageUserAccountForm or app.auth.forms.ManageAgencyUserAccountForm
    """
    update_object(
        {
            'title': form.title.data,
            'organization': form.organization.data,
            'notification_email': form.notification_email.data,
            'phone_number': form.phone_number.data,
            'fax_number': form.fax_number.data,
            'mailing_address': create_mailing_address(
                form.address_one.data or None,
                form.city.data or None,
                form.state.data or None,
                form.zipcode.data or None,
                form.address_two.data or None)
        },
        Users,
        (current_user.guid, current_user.auth_user_type))

    if current_user.is_agency and current_user.default_agency_ein != form.default_agency.data:
        update_object(
            {'is_primary_agency': False},
            AgencyUsers,
            (current_user.guid, current_user.auth_user_type, current_user.default_agency_ein)
        )
        update_object(
            {'is_primary_agency': True},
            AgencyUsers,
            (current_user.guid, current_user.auth_user_type, form.default_agency.data)
        )


def is_safe_url(target):
    """ Taken from http://flask.pocoo.org/snippets/62/ with the help of Liam Neeson """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def find_user_by_email(email):
    """
    Find a user by email address stored in the database.
    If LDAP login is being used, non-agency users and users
    without an LDAP auth type are ignored.
    If OAUTH login is being used, anonymous users are ignored.

    :param email: Email address
    :return: User object or None if no user found.
    """
    if current_app.config['USE_LDAP']:
        user = Users.query.filter_by(
            email=email,
            auth_user_type=user_type_auth.AGENCY_LDAP_USER
        ).first()
        return user if user.agencies.all() else None
    elif current_app.config['USE_OAUTH']:
        from sqlalchemy import func
        return Users.query.filter(
            func.lower(Users.email) == email.lower(),
            Users.auth_user_type.in_(user_type_auth.AGENCY_USER_TYPES)
        ).first()
    return None


def oauth_user_web_service_request(method="GET", user_session=session):
    """
    Invoke the OAuth User Web Service with specified method.
    https://nyc4d.nycnet/nycid/mobile.shtml#get-oauth-user-web-service

    * Assumes the access token is stored in the session. *

    :returns: response for user web services request
    """
    return _web_services_request(
        USER_ENDPOINT,
        {"accessToken": user_session['token']['access_token']},
        method=method
    )


def revoke_and_remove_access_token(user_session):
    """
    Invoke the Delete OAuth User Web Service
    to revoke an access token and remove the
    token from the session.

    * Assumes the access token is stored in the session. *

    WARNING
    -------
    In the NYC.ID DEV environment, access tokens are
    automatically revoked on IDP logout, so the revocation
    executed in here will fail and an error will be logged!

    Once the change hits NYC.ID PRD, this function should
    be renamed to "remove_access_token" and should only
    consist of "session.pop('token')".

    """
    # FIXME: see WARNING above
    if user_session:
        _check_web_services_response(
            oauth_user_web_service_request("DELETE", user_session=user_session),
            error_msg.REVOKE_TOKEN_FAILURE)
        user_session.pop('token')
    else:
        session.pop('token')


def fetch_user_json():
    """
    Invoke the Get OAuth User Web Service to fetch
    a JSON-formatted user.
    https://nyc4d.nycnet/nycid/search.shtml#json-formatted-users

    * Assumes the access token is stored in the session. *

    :return: response status code, user data json dict
    """
    response = oauth_user_web_service_request()
    return response.status_code, response.json()


def handle_user_data(guid,
                     user_type,
                     email,
                     first_name=None,
                     middle_initial=None,
                     last_name=None,
                     terms_of_use=None,
                     email_validation_flag=None,
                     token=None,
                     next_url=None):
    """
    Interpret the result of processing the specified
    user data and act accordingly:
    - If a redirect url is returned, redirect to that url.
    - If a user is returned, login that user and return
      a redirect to the specified next_url, the home page url,
      or to the 404 page if next_url is provided and is unsafe.
    """
    redirect_required, user_or_url = _process_user_data(
        guid,
        user_type,
        email,
        first_name,
        middle_initial,
        last_name,
        terms_of_use,
        email_validation_flag
    )
    if redirect_required:
        return redirect(user_or_url)
    else:
        login_user(user_or_url)
        _session_regenerate_persist_token()

        if not is_safe_url(next_url):
            return abort(400, error_msg.UNSAFE_NEXT_URL)

        return redirect(next_url or url_for('main.index', fresh_login=True))


def _session_regenerate_persist_token():
    token = session['token']
    token_expires_at = session['token_expires_at']
    session.regenerate()
    session['token'] = token
    session['token_expires_at'] = token_expires_at


def _process_user_data(guid,
                       user_type,
                       email,
                       first_name,
                       middle_initial,
                       last_name,
                       terms_of_use,
                       email_validation_flag):
    """
    Kickoff email validation (if the user did not authenticate
    with a federated identity) or terms-of-use acceptance if the
    user has not validated their email or has not accepted the
    latest terms of use version.

    Otherwise, create or update a user with the specified fields.

    If no first_name is provided, the mailbox portion of the email
    will be used (e.g. jdoe@records.nyc.gov -> first_name: jdoe).

    If a user cannot be found using the specified guid and user_type,
    a second attempt is made with the specified email.

    NOTE: A user's agency is not determined here. After login, a user's
    agency supervisor must email us requesting that user be added
    to the agency.

    :return: (redirect required?, user that has been found or created OR redirect url)
    """
    possible_redirect_actions = [{
        "function": _validate_email,
        "args": [email_validation_flag, guid, email, user_type]
    }, {
        "function": _accept_terms_of_use,
        "args": [terms_of_use, guid, user_type]
    }]
    for action in possible_redirect_actions:
        redirect_url = action["function"](*action["args"])
        if redirect_url:
            return True, redirect_url

    _enroll(guid, user_type)

    mailbox, domain = email.split('@')

    if first_name is None:
        first_name = mailbox

    user = Users.query.filter_by(guid=guid, auth_user_type=user_type).first()
    if user is None and user_type in user_type_auth.AGENCY_USER_TYPES:
        user = find_user_by_email(email)

    # update or create user
    if user is not None:
        _update_user_data(user,
                          guid,
                          user_type,
                          email,
                          first_name,
                          middle_initial,
                          last_name)
    else:
        user = Users(
            guid=guid,
            auth_user_type=user_type,
            first_name=first_name,
            middle_initial=middle_initial,
            last_name=last_name,
            email=email,
            email_validated=True,
            terms_of_use_accepted=True,
        )
        create_object(user)

    return False, user


def _update_user_data(user, guid, user_type, email, first_name, middle_initial, last_name):
    """
    Update specified user with the information provided, which is
    assumed to have originated from an NYC Service Account, and set
    `email_validated` and `terms_of_use_accepted` (this function
    should be called AFTER email validation and terms-of-use acceptance
    has been completed).

    Update any database objects this user is associated with.
    - user_requests
    - events
    In order to prevent a possbile negative performance impact
    (due to foreign keys CASCADE), guid and user_type are compared with
    stored user attributes and are excluded from the update if both are identical.
    """
    updated_data = {
        'email': email,
        'first_name': first_name,
        'middle_initial': middle_initial,
        'last_name': last_name,
        'email_validated': True,
        'terms_of_use_accepted': True,
    }
    if guid != user.guid or user_type != user.auth_user_type:
        updated_data.update(
            guid=guid,
            auth_user_type=user_type
        )
        update_events_values = Events.query.filter(Events.new_value['user_guid'].astext == user.guid,
                                                   Events.new_value[
                                                       'auth_user_type'].astext == user.auth_user_type).all()
        for event in update_events_values:
            update_object(
                {'new_value': {'user_guid': guid,
                               'auth_user_type': user_type}},
                Events,
                event.id
            )
    update_object(
        updated_data,
        Users,
        (user.guid, user.auth_user_type)
    )


def _validate_email(email_validation_flag, guid, email_address, user_type):
    """
    If the user did not log in via NYC.ID
    (i.e. user_type is not 'EDIRSSO'),
    no email validation is necessary.

    A email is considered to have been validated if the
    email validation flag is
    - not provided
    - 'TRUE'
    - 'true'
    - 'Unavailable'
    - True

    If the email validation flag is not one of the above (i.e. FALSE),
    the Email Validation Web Service is invoked.

    If the returned validation status equals false,
    return url to the 'Email Confirmation Required' page
    where the user can request a validation email.

    :return: redirect url or None
    """
    if user_type == user_type_auth.PUBLIC_USER_NYC_ID and (
                    email_validation_flag is not None and
                    email_validation_flag not in ['true', 'TRUE', 'Unavailable', True]):
        response = _web_services_request(
            EMAIL_VALIDATION_STATUS_ENDPOINT,
            {"guid": guid}
        )
        _check_web_services_response(response, error_msg.EMAIL_STATUS_CHECK_FAILURE)
        if not response.json().get('validated', False):
            # redirect to Email Confirmation Required page
            return '{url}?emailAddress={email_address}&target={target}'.format(
                url=urljoin(current_app.config['WEB_SERVICES_URL'],
                            EMAIL_VALIDATION_ENDPOINT),
                email_address=email_address,
                target=b64encode(
                    urljoin(request.host_url, url_for(login_manager.login_view)).encode()
                ).decode()
            )


def _accept_terms_of_use(terms_of_use, guid, user_type):
    """
    If the user has logged in using the NYC Employees button
    (i.e. the user_type is 'Saml2In: NYC Employees'),
    no TOU acceptance is necessary.

    Otherwise, invoke the Terms of Use Web Service to determine
    if the user has accepted the latest TOU version.
    If not, return url to 'NYC. TOU' page where the user can
    accept the latest terms of use.

    :return: redirect url or None
    """
    if user_type != user_type_auth.AGENCY_USER and terms_of_use is not True:  # must be True, nothing else!
        response = _web_services_request(
            TOU_STATUS_ENDPOINT,
            {
                "guid": guid,
                "userType": user_type
            }
        )
        _check_web_services_response(response, error_msg.TOU_STATUS_CHECK_FAILURE)
        if not response.json().get('current', False):
            # redirect to NYC. TOU page
            return '{url}?target={target}'.format(
                url=urljoin(current_app.config['WEB_SERVICES_URL'],
                            TOU_ENDPOINT),
                target=b64encode(
                    urljoin(request.host_url, url_for(login_manager.login_view)).encode()
                ).decode()
            )


def _enroll(guid, user_type):
    """
    Retrieve enrollment statues for a specified
    user and, if the user has not yet been enrolled,
    create an enrollment record for that user.
    """
    params = {
        "guid": guid,
        "userType": user_type
    }
    response = _web_services_request(
        ENROLLMENT_STATUS_ENDPOINT,
        params.copy()  # signature regenerated
    )
    _check_web_services_response(response, error_msg.ENROLLMENT_STATUS_CHECK_FAILURE)
    if response.status_code != 200 or not response.json():  # empty json = no enrollment record
        _check_web_services_response(
            _web_services_request(
                ENROLLMENT_ENDPOINT,
                params,
                method='PUT'
            ),
            error_msg.ENROLLMENT_FAILURE)


def _unenroll(guid, user_type):
    """
    Delete an enrollment.
    *Included for possible future use.*
    """
    _check_web_services_response(
        _web_services_request(
            ENROLLMENT_ENDPOINT,
            {
                "guid": guid,
                "userType": user_type
            },
            method='DELETE'
        ),
        error_msg.UNENROLLMENT_FAILURE)


def _check_web_services_response(response, msg):
    """
    Log an error message if the specified response's
    status code is not 200.
    """
    if response.status_code != 200:
        current_app.logger.error("{}\n{}".format(msg, dumps(response.json(), indent=2)))


def _web_services_request(endpoint, params, method='GET'):
    """
    Perform a request on an NYC.ID Web Services endpoint.
    'userName' and 'signature' are added to the specified params.

    :param endpoint: web services endpoint (e.g. "/account/validateEmail.htm")
    :param params: request parameters excluding 'userName' and 'signature'
    :param method: HTTP method
    :return: request response
    """
    current_app.logger.info("NYC.ID Web Services Requests: {} {}".format(method, endpoint))
    params['userName'] = current_app.config['NYC_ID_USERNAME']
    # don't refactor to use dict.update() - signature relies on userName param
    params['signature'] = _generate_signature(
        current_app.config['NYC_ID_PASSWORD'],
        _generate_string_to_sign(method, endpoint, params)
    )
    req = None
    # SSLError with 'bad signature' is sometimes thrown when sending the request which causes an nginx error and 502
    # resending the request resolves the issue
    for i in range(0, 5):
        try:
            req = requests.request(
                method,
                urljoin(current_app.config['WEB_SERVICES_URL'], endpoint),
                verify=current_app.config['VERIFY_WEB_SERVICES'],
                params=params  # query string parameters always used
            )
        except SSLError:
            continue
        break
    return req


def _generate_string_to_sign(method, path, params):
    """
    Generate a string that can be signed to produce an
    authentication signature.

    :param method: HTTP method
    :param path: path part of HTTP request URI
    :param params: querystring parameters
    :return: string to sign
    """
    return '{method}{path}{parameter_values}'.format(
        method=method,
        # ensure path begins with a forward slash
        path=path if path[0] == '/' else '/' + path,
        parameter_values=''.join([
            # must be sorted alphabetically by parameter name
            str(val) for param, val in sorted(params.items())
        ])
    )


def _generate_signature(password, string):
    """
    Generate an NYC.ID Web Services authentication signature using HMAC-SHA1

    https://nyc4d.nycnet/nycid/web-services.shtml#signature

    :param password: NYC.ID Service Account password
    :param string: string to sign
    :return: the authentication signature or None on failure
    """
    signature = None
    try:
        hmac_sha1 = hmac.new(key=password.encode(),
                             msg=string.encode(),
                             digestmod=sha1)
        signature = hmac_sha1.hexdigest()
    except Exception as e:
        current_app.logger.error("Failed to generate NYC ID.Web Services "
                                 "authentication signature: ", e)
    return signature


# LDAP -----------------------------------------------------------------------------------------------------------------

def ldap_authentication(email, password):
    """
    Authenticate the provided user with an LDAP Server.
    :param email: Users username
    :param password: Users password
    :return: Boolean
    """
    conn = _ldap_server_connect()

    users = conn.search(search_base=current_app.config['LDAP_BASE_DN'],
                        search_filter='(mail={email})'.format(email=email), attributes='dn')

    if users and len(conn.entries) >= 1:
        return conn.rebind(conn.entries[0].entry_dn, password)


def _ldap_server_connect():
    """
    Connect to an LDAP server
    :return: LDAP Context
    """
    ldap_server = current_app.config['LDAP_SERVER']
    ldap_port = int(current_app.config['LDAP_PORT'])
    ldap_use_tls = current_app.config['LDAP_USE_TLS']
    ldap_key_path = current_app.config['LDAP_KEY_PATH']
    ldap_sa_bind_dn = current_app.config['LDAP_SA_BIND_DN']
    ldap_sa_password = current_app.config['LDAP_SA_PASSWORD']

    tls = Tls(validate=ssl.CERT_NONE, local_private_key_file=ldap_key_path)

    if ldap_use_tls:
        server = Server(ldap_server, ldap_port, tls=tls, use_ssl=True)

    else:
        server = Server(ldap_server, ldap_port)

    conn = Connection(server, ldap_sa_bind_dn, ldap_sa_password, auto_bind=True)

    return conn
