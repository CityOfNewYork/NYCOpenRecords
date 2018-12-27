"""
.. module:: auth.views.

   :synopsis: Authentication utilities for NYC OpenRecords

"""
import ssl
from json import dumps
from urllib.parse import urljoin, urlparse

import hmac
import requests
from base64 import b64encode
from flask import (
    abort, current_app, flash, jsonify, redirect, request, session, url_for
)
from flask_login import current_user, login_user, logout_user
from hashlib import sha1
from ldap3 import Connection, Server, Tls
from requests.exceptions import SSLError

from app import (
    login_manager,
    sentry
)
from app.auth.constants import error_msg
from app.constants.web_services import (
    EMAIL_VALIDATION_ENDPOINT, EMAIL_VALIDATION_STATUS_ENDPOINT,
    USER_SEARCH_ENDPOINT, USER_ENDPOINT
)
from app.lib.utils import eval_request_bool
from app.lib.db_utils import create_object, update_object
from app.lib.onelogin.saml2.auth import OneLogin_Saml2_Auth
from app.lib.onelogin.saml2.utils import OneLogin_Saml2_Utils
from app.lib.user_information import create_mailing_address
from app.models import AgencyUsers, Events, Requests, Users


@login_manager.user_loader
def user_loader(guid: str) -> Users:
    """Given a GUID return the associated User object.

    Args:
        guid (str): User ID (GUID) of the user to retrieve from the database.

    Returns:
        Users: User object from the database or None.
    """
    return Users.query.filter_by(guid=guid).one_or_none()


def init_saml_auth(onelogin_request):
    """Initialize a SAML SP from a dictionary representation of a Flask request.

    Args:
        onelogin_request (dict): Dictionary representation of a Flask Request object.

    Returns:
        OneLogin_Saml2_Auth: SAML SP Instance.

    """
    saml_sp = OneLogin_Saml2_Auth(onelogin_request, custom_base_path=current_app.config['SAML_PATH'])
    return saml_sp


def prepare_onelogin_request(flask_request):
    """Convert a Flask request object to a dictionary for use with OneLogin SAML.

    Args:
        flask_request (Flask.Request): Flask Request object.

    Returns:
        dict: Dictionary of Flask Request fields for OneLogin

    """
    url_data = urlparse(flask_request.url)
    return {
        'https': 'on' if flask_request.scheme == 'https' else 'off',
        'http_host': flask_request.host,
        'server_port': url_data.port,
        'script_name': flask_request.path,
        'request_uri': url_for('auth.saml', _external=True),
        'get_data': flask_request.args.copy(),
        # Uncomment if using ADFS as IdP, https://github.com/onelogin/python-saml/pull/144
        # 'lowercase_urlencoding': True,
        'post_data': flask_request.form.copy()
    }


def saml_sso(saml_sp):
    """ Handle Single Sign-On for SAML.

    Calls the login function in the OneLogin python3-saml library to generate an Assertion Request to the IdP.

    Args:
        saml_sp (OneLogin_Saml2_Auth): Saml SP Instance

    Returns:
        Response Object: Redirect the user to the IdP for SSO.

    """
    return redirect(saml_sp.login())


def saml_sls(saml_sp):
    """Process a SAML LogoutResponse from the IdP

    Args:
        saml_sp (OneLogin_Saml2_Auth): SAML SP Instance

    Returns:
        Response Object: Redirect the user to the Home Page.

    """
    dscb = lambda: session.clear()
    url = saml_sp.process_slo(delete_session_cb=dscb)
    errors = saml_sp.get_errors()
    update_object(
        {
            'session_id': None
        },
        Users,
        current_user.guid
    )
    logout_user()
    if not errors:
        return redirect(url) if url else redirect(url_for('main.index'))
    else:
        current_app.logger.exception("Errors on SAML Logout:\n{errors}".format(errors='\n'.join(errors)))
        flash("Sorry! An unexpected error has occurred. Please try again later.", category='danger')
        return redirect(url_for('main.index'))


def saml_slo(saml_sp):
    """Generate a SAML LogoutRequest for the user.

    Args:
        saml_sp (OneLogin_Saml2_Auth): SAML SP Instance

    Returns:
        Response Object: Redirect the user to the IdP for SLO.
    """
    name_id = None
    session_index = None
    if 'samlNameId' in session:
        name_id = session['samlNameId']
    if 'samlSessionIndex' in session:
        session_index = session['samlSessionIndex']

    return saml_sp.logout(name_id=name_id, session_index=session_index)


def saml_acs(saml_sp, onelogin_request):
    """Process a SAML Assertion for the user

    Args:
        saml_sp (OneLogin_Saml2_Auth): SAML SP Instance

    Returns:
        Response Object: Redirect the user to the appropriate page for the next step.
            If the user needs to validate their email, they are redirected to the IdP
            Otherwise, the user is redirected to a valid RelayState.
            If RelayState is invalid, the user is redirected to the home page.

    """

    saml_sp.process_response()
    errors = saml_sp.get_errors()

    if len(errors) == 0:
        session['samlUserdata'] = saml_sp.get_attributes()
        session['samlNameId'] = saml_sp.get_nameid()
        session['samlSessionIndex'] = saml_sp.get_session_index()

        # Log User In
        user_data = {k: v[0] if len(v) else None for (k, v) in session['samlUserdata'].items()}

        nycid_user_data = get_nycid_user_data(user_data['GUID'])

        if not nycid_user_data.get('validated', False):
            email_validation_url = _validate_email(nycid_user_data.get('validated', False), nycid_user_data.get('id'),
                                                   nycid_user_data.get('email'))
            return redirect(email_validation_url)

        user = _process_user_data(
            guid=nycid_user_data.get('id', None),
            first_name=nycid_user_data.get('firstName', None),
            middle_initial=nycid_user_data.get('middleInitial', None),
            last_name=nycid_user_data.get('lastName', None),
            email=nycid_user_data.get('email', None),
            email_validated=nycid_user_data.get('validated', False),
            is_nyc_employee=nycid_user_data.get('nycEmployee', False),
            has_nyc_account=nycid_user_data.get('hasNYCAccount', False),
            active=nycid_user_data.get('active', False),
            terms_of_use_accepted=nycid_user_data.get('termsOfUse', False),
            is_anonymous_requester=False
        )
        login_user(user)

        self_url = OneLogin_Saml2_Utils.get_self_url(onelogin_request)

        if 'RelayState' in request.form and self_url != request.form['RelayState']:
            return saml_sp.redirect_to(request.form['RelayState'])

        return redirect(url_for('main.index'))
    return abort(500)


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
            '_mailing_address': create_mailing_address(
                form.address_one.data or None,
                form.city.data or None,
                form.state.data or None,
                form.zipcode.data or None,
                form.address_two.data or None)
        },
        Users,
        current_user.guid
    )

    if current_user.is_agency and current_user.default_agency_ein != form.default_agency.data:
        update_object(
            {'is_primary_agency': False},
            AgencyUsers,
            (current_user.guid, current_user.default_agency_ein)
        )
        update_object(
            {'is_primary_agency': True},
            AgencyUsers,
            (current_user.guid, form.default_agency.data)
        )


def is_safe_url(target):
    """Determine if a URL is safe to redirect the user to.

    Source: http://flask.pocoo.org/snippets/62/

    Args:
        target (str): URL to redirect the user to.

    Returns:
        bool: True if the URL is safe.

    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def find_user_by_email(email):
    """Find a user by email address stored in the database.

    If LDAP login is being used, non-agency users and users without an LDAP auth type are ignored.
    If OAuth or SAML login is being used, anonymous users are ignored.

    Args:
        email (str): Email address to search by.

    Returns:
        Users: User object or None if no user found.

    """
    if current_app.config['USE_LDAP']:
        user = Users.query.filter_by(
            email=email
        ).first()
        return user if user.agencies.all() else None
    elif current_app.config['USE_OAUTH'] or current_app.config['USE_SAML']:
        from sqlalchemy import func
        return Users.query.filter(
            func.lower(Users.email) == email.lower()
        ).first()
    return None


def oauth_user_web_service_request(method="GET"):
    """
    Invoke the OAuth User Web Service with specified method.
    https://nyc4d.nycnet/nycid/mobile.shtml#get-oauth-user-web-service

    * Assumes the access token is stored in the session. *

    :returns: response for user web services request
    """
    return _web_services_request(
        USER_ENDPOINT,
        {"accessToken": session['token']['access_token']},
        method=method
    )


def _session_regenerate_persist_token():
    """
    Regenerate the Session ID while persisting session contents on Server Side.

    TODO @joelbcastillo: Determine if we need to manually persist session data.

    """
    token = session['token']
    token_expires_at = session['token_expires_at']
    session.regenerate()
    session['token'] = token
    session['token_expires_at'] = token_expires_at


def _process_user_data(guid,
                       email,
                       first_name,
                       middle_initial,
                       last_name,
                       email_validated,
                       is_nyc_employee,
                       has_nyc_account,
                       active,
                       terms_of_use_accepted,
                       is_anonymous_requester):
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
    mailbox, domain = email.split('@')

    if first_name is None:
        first_name = mailbox

    user = Users.query.filter_by(guid=guid).first()
    if user is None:
        user = find_user_by_email(email)

    # update or create user
    if user is not None:
        _update_user_data(
            user,
            guid,
            email,
            first_name,
            middle_initial,
            last_name,
            email_validated,
            is_nyc_employee,
            has_nyc_account,
            active,
            terms_of_use_accepted,
            is_anonymous_requester
        )
    else:
        user = Users(guid=guid,
                     email=email,
                     first_name=first_name,
                     middle_initial=middle_initial,
                     last_name=last_name,
                     email_validated=email_validated,
                     is_nyc_employee=is_nyc_employee,
                     has_nyc_account=has_nyc_account,
                     active=active,
                     terms_of_use_accepted=terms_of_use_accepted,
                     is_anonymous_requester=is_anonymous_requester
                     )
        create_object(user)

    return user


def _update_user_data(user, guid, email, first_name, middle_initial, last_name, email_validated, is_nyc_employee=False,
                      has_nyc_account=False, active=False, terms_of_use_accepted=False, is_anonymous_requester=False):
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

    Update search index for searching by assigned user.
    """
    updated_data = {
        'guid': guid,
        'first_name': first_name,
        'middle_initial': middle_initial,
        'last_name': last_name,
        'email': email,
        'email_validated': email_validated,
        'is_nyc_employee': is_nyc_employee,
        'has_nyc_account': has_nyc_account,
        'active': active,
        'terms_of_use_accepted': terms_of_use_accepted,
        'is_anonymous_requester': is_anonymous_requester
    }
    if guid != user.guid:
        updated_data.update(
            guid=guid
        )
        update_events_values = Events.query.filter(Events.new_value['user_guid'].astext == user.guid).all()

        for event in update_events_values:
            update_object(
                {'new_value': {'user_guid': guid}},
                Events,
                event.id
            )

        update_object(
            updated_data,
            Users,
            user.guid
        )

        for user_request in user.user_requests:
            Requests.query.filter_by(id=user_request.request_id).one().es_update()

    else:
        update_object(
            updated_data,
            Users,
            (user.guid)
        )


def _validate_email(email_validation_flag, guid, email_address):
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
    if email_validation_flag == str(False):
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


def get_nycid_user_data(guid):
    """
    Validate whether the user is a NYC Employee.
    If the returned validation status equals false,
    return url to the 'Email Confirmation Required' page
    where the user can request a validation email.

    :return: redirect url or None
    """
    response = _web_services_request(
        USER_SEARCH_ENDPOINT,
        {"guid": guid}
    )
    _check_web_services_response(response, error_msg.USER_DATA_RETRIEVAL_FAILURE)
    return response.json()


def _check_web_services_response(response, msg=''):
    """
    Log an error message if the specified response's
    status code is not 200.
    """
    if response.status_code == 404:
        current_app.logger.error("{}".format(msg))
    elif response.status_code != 200:
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
            sentry.captureException()
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
        sentry.captureException()
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
