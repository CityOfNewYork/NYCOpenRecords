"""
.. module:: auth.views.

   :synopsis: Authentication utilities for NYC OpenRecords
"""
import ssl
import hmac
import requests

from hashlib import sha1
from base64 import b64encode
from urllib.parse import urljoin

from flask import (
    current_app,
    session,
    url_for,
    request,
)
from flask_login import login_user
from app import login_manager
from app.models import Users
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
from app.lib.db_utils import create_object, update_object

from ldap3 import Server, Tls, Connection


# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'True'  # TODO: if endpoint does not use https


@login_manager.user_loader
def user_loader(user_id):
    """
    Given a user_id (GUID + UserType), return the associated User object.

    :param unicode user_id: user_id (GUID + UserType) of user to retrieve
    :return: User object
    """
    user_id = user_id.split(USER_ID_DELIMITER)
    return Users.query.filter_by(guid=user_id[0], auth_user_type=user_id[1]).first()


def find_user_by_email(email):
    """
    Find a user by email address stored in the database.
    If LDAP login is being used, non-agency users are ignored.

    :param email: Email address
    :return: User object or None if no user found.
    """
    criteria = {'email': email}
    if current_app.config['USE_LDAP']:
        criteria['is_agency_active'] = True
    return Users.query.filter_by(**criteria).first()


def revoke_and_remove_access_token():
    """
    Invoke the Delete OAuth User Web Service
    to revoke an access token and remove the
    token from the session.

    Assumes the access token (i.e. 'token')
    is stored in the session.
    """
    response = _web_services_request(
        USER_ENDPOINT,
        {
            "accessToken": session['token'],
            "userName": current_app.config['NYC_ID_USERNAME'],
        },
        method="DELETE"
    )
    # TODO: handle error
    session.pop('token')


def handle_user_data(guid,
                     user_type,
                     email,
                     first_name=None,
                     middle_initial=None,
                     last_name=None,
                     terms_of_use=None,
                     email_validation_flag=None,
                     return_to_url=None):
    """
    Essentially a wrapper for _process_user_data.
    If a redirect url is returned, return that url.
    If a user is returned, login that user and return
    the specified return_to_url or the home page url.
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
        return user_or_url
    else:
        login_user(user_or_url)
        return return_to_url if return_to_url else url_for('main.index')


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

    import ipdb
    ipdb.set_trace()
    
    mailbox, domain = email.split['@']

    if first_name is None:
        first_name = mailbox

    user = Users.query.filter_by(guid=guid, auth_user_type=user_type).first()
    if user is None:
        user = find_user_by_email(email)

    if user is not None:
        _update_user_data(user,
                          guid,
                          user_type,
                          email,
                          first_name,
                          middle_initial,
                          last_name)
    else:
        user = create_object(Users(
            guid=guid,
            auth_user_type=user_type,
            first_name=first_name,
            middle_initial=middle_initial,
            last_name=last_name,
            email=email,
            email_validated=True,
            terms_of_use_accepted=True,
        ))

    return False, user


def _update_user_data(user, guid, user_type, email, first_name, middle_initial, last_name):
    """
    Update specified user with the information provided, which is
    assumed to have originated from an NYC Service Account, and set
    `email_validated` and `terms_of_use_accepted` (this function
    should be called AFTER email validation and terms-of-use acceptance
    has been completed).
    """
    update_object(
        {
            'guid': guid,
            'auth_user_type': user_type,
            'email': email,
            'first_name': first_name,
            'middle_initial': middle_initial,
            'last_name': last_name,
            'email_validated': True,
            'terms_of_use_accepted': True,
        },
        Users,
        (user.guid, user.auth_user_type)
    )


def _validate_email(email_validation_flag, guid, email_address, user_type):
    """
    If the user_type is not associated with a federated identity,
    no email validation is necessary.

    A email is considered to have been validated if the
    email validation flag is
    - not provided
    - 'TRUE'
    - 'true'
    - 'Unavailable'
    - True

    If the email validation flag is not one of the above (i.e. FALSE)
    and the user_type is not associated with a federated identity,
    the Email Validation Web Service is invoked.

    If the returned validation status equals false,
    return url to the 'Email Confirmation Required' page
    where the user can request a validation email.

    :return: redirect url or None
    """
    if user_type in user_type_auth.FEDERATED_USER_TYPES or (
            email_validation_flag is not None
            and email_validation_flag not in ['true', 'TRUE', 'Unavailable', True]):
        response = _web_services_request(
            EMAIL_VALIDATION_STATUS_ENDPOINT,
            {
                "guid": guid,
                "userName": current_app.config['NYC_ID_USERNAME']
            }
        )
        # TODO: handle and log errors
        if not response.json()['validated']:
            # redirect to Email Confirmation Required page
            return '{url}?emailAddress={email_address}&target={target}'.format(
                url=urljoin(current_app.config['WEB_SERVICES_URL'],
                            EMAIL_VALIDATION_ENDPOINT),
                email_address=email_address,
                target=b64encode(
                    # b'https://openrecords-staging.appdev.records.nycnet/'
                    urljoin(request.host_url, url_for('auth.login')).encode()
                ).decode()
            )


def _accept_terms_of_use(terms_of_use, guid, user_type):
    """
    If the user has logged in using the NYC Employees button
    (assumes this means their user_type is 'Saml2In: NYC Employees'),
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
                "userName": current_app.config['NYC_ID_USERNAME'],
                "userType": user_type,
            }
        )
        # TODO: handle error (abort(500) if necessary)
        if not response.json()['current']:
            # redirect to NYC. TOU page
            return '{url}?target={target}'.format(
                url=urljoin(current_app.config['WEB_SERVICES_URL'],
                            TOU_ENDPOINT),
                target=b64encode(
                    # b'https://openrecords-staging.appdev.records.nycnet/'
                    urljoin(request.host_url, url_for('auth.login')).encode()
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
        "userType": user_type,
        "userName": current_app.config['NYC_ID_USERNAME'],
    }
    response = _web_services_request(
        ENROLLMENT_STATUS_ENDPOINT,
        params.copy()  # 'signature' will be added
    )
    # TODO: handle error (if response.status_code != 200, then check which code)
    if not response.json():  # empty json = no enrollment record
        response = _web_services_request(
            ENROLLMENT_ENDPOINT,
            params,
            method='PUT'
        )
        # TODO: handle error


def _unenroll(guid, user_type):
    """
    Delete an enrollment.
    *Included for possible future use.*
    """
    response = _web_services_request(
        ENROLLMENT_ENDPOINT,
        {
            "guid": guid,
            "userType": user_type,
            "userName": current_app.config['NYC_ID_USERNAME']
        },
        method='DELETE'
    )
    # TODO: handle error


def _web_services_request(endpoint, params, method='GET'):
    params['signature'] = _generate_signature(
        current_app.config['NYC_ID_PASSWORD'],
        _generate_string_to_sign(method, endpoint, params)
    )
    return requests.request(
        method,
        urljoin(current_app.config['WEB_SERVICES_URL'], endpoint),
        verify=current_app.config['VERIFY_WEB_SERVICES'],
        params=params  # query string parameters always used
    )


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
