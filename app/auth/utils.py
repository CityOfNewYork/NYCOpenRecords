"""
.. module:: auth.views.

   :synopsis: Authentication utilities for NYC OpenRecords
"""
import ssl
import hmac
import requests

from hashlib import sha1
from urllib.parse import urljoin

from flask import (
    current_app,
    session,
    url_for,
    redirect,
)
from flask_login import current_user
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


# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'True'  # TODO: if endpoint does not use https


def remove_and_revoke_access_token():
    """
    Invoke the Delete OAuth User Web Service
    to revoke an access token and remove the
    token from the session.

    Assumes the access token (i.e. 'token')
    is stored in the session.
    """
    params = {
        "accessToken": session['token'],
        "userName": current_app.config['NYC_ID_USERNAME']
    }
    params['signature'] = generate_signature(
        current_app.config['NYC_ID_PASSWORD'],
        generate_string_to_sign(
            USER_ENDPOINT,
            params,
            method="DELETE"
        )
    )
    response = requests.delete(
        urljoin(current_app.config["WEB_SERVICE_URL"],
                USER_ENDPOINT),
        data=params
    )
    session.pop('token')


def process_user_data(guid,
                      user_type,
                      email,
                      first_name=None,
                      middle_initial=None,
                      last_name=None,
                      terms_of_use=None,
                      email_validation_flag=None):
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

    :return: user that has been found or created
    """
    validate_email(email_validation_flag, guid, email, user_type)
    accept_terms_of_use(terms_of_use, guid, user_type)
    enroll(guid, user_type)

    mailbox, domain = email.split['@']

    if first_name is None:
        first_name = mailbox

    user = Users.query.filter_by(guid=guid, auth_user_type=user_type).first()
    if user is None:
        user = find_user_by_email(email)

    if user is not None:
        update_user_data(user,
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

    return user


def update_user_data(user, guid, user_type, email, first_name, middle_initial, last_name):
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


def validate_email(email_validation_flag, guid, email_address, user_type):
    """
    If the user_type is not associated with a federated identity,
    no email validation is necessary.

    A email is considered to have been validated if the
    email validation flag is
    - not provided
    - 'TRUE'
    - 'Unavailable'
    - True

    If the email validation flag is not one of the above (i.e. FALSE)
    and the user_type is not associated with a federated identity,
    the Email Validation Web Service is invoked.

    If the returned validation status equals false,
    the user is sent to the 'Email Confirmation Required' page
    to request another validation email.

    """
    if user_type not in user_type_auth.FEDERATED_USER_TYPES or (
            email_validation_flag is not None
            and email_validation_flag not in ['TRUE', 'Unavailable', True]):
        string_to_sign = 'GET{path}{guid}{user_name}'.format(
            path=EMAIL_VALIDATION_STATUS_ENDPOINT,
            guid=guid,
            user_name=current_app.config['NYC_ID_USERNAME'])
        response = requests.get(
            urljoin(current_app.config['WEB_SERVICES_URL'],
                    EMAIL_VALIDATION_STATUS_ENDPOINT),
            {
                'guid': guid,
                'userName': current_app.config['NYC_ID_USERNAME'],
                'signature': generate_signature(current_app.config['NYC_ID_PASSWORD'],
                                                string_to_sign)
            })
        # TODO: handle error
        if not response.json()['validated']:
            # redirect to Email Confirmation Required page
            redirect('{url}?{email_address}&{target}'.format(
                url=urljoin(current_app.config['WEB_SERVICES_URL'],
                            EMAIL_VALIDATION_ENDPOINT),
                email_address=email_address,
                target=url_for('auth.login')
            ))


def accept_terms_of_use(terms_of_use, guid, user_type):
    """
    If the user has logged in using the NYC Employees button
    (assumes this means their user_type is 'Saml2In: NYC Employees'),
    no TOU acceptance is necessary.

    Invokes the Terms of Use Web Service to determine if the
    user has accepted the latest TOU version. If not, the user
    is sent to the 'NYC. TOU' page to accept the latest
    terms of use.

    """
    # TODO: check this if statement
    if terms_of_use is not True or user_type != user_type_auth.AGENCY_USER:  # must be True, nothing else!
        string_to_sign = 'GET{path}{guid}{user_name}{user_type}'.format(
            path=TOU_STATUS_ENDPOINT,
            guid=guid,
            user_name=current_app.config['NYC_ID_USERNAME'],
            user_type=user_type
        )
        response = requests.get(
            urljoin(current_app.config['WEB_SERVICES_URL'],
                    TOU_STATUS_ENDPOINT),
            {
                'guid': guid,
                'userName': current_app.config['NYC_ID_USERNAME'],
                'userType': user_type,
                'signature': generate_signature(current_app.config['NYC_ID_PASSWORD'],
                                                string_to_sign)
            })
        # TODO: handle error (abort(500))
        if not response.json()['current']:
            # redirect to NYC. TOU page
            redirect('{url}?{target}'.format(
                url=urljoin(current_app.config['WEB_SERVICES_URL'],
                            TOU_ENDPOINT),
                target=url_for('auth.login')
            ))


def enroll(guid, user_type):
    """
    Retrieve enrollment statues for a specified
    user and, if the user has not yet been enrolled,
    create an enrollment record for that user.
    """
    params = {  # TODO: test with test info
        "guid": guid,
        "userType": user_type,
        "userName": current_user.config['NYC_ID_USERNAME'],
    }
    params["signature"] = generate_signature(
        current_app.config['NYC_ID_PASSWORD'],
        generate_string_to_sign(
            ENROLLMENT_STATUS_ENDPOINT,
            params
        )
    )
    response = requests.get(
        urljoin(current_app.config['WEB_SERVICE_URL'],
                ENROLLMENT_STATUS_ENDPOINT),
        params
    )
    # TODO: handle error (if response.status_code != 200, then check which code)
    if not response.json():  # empty json = no enrollment record
        string_to_sign = 'PUT{path}{guid}{user_name}{user_type}'.format(
            path=ENROLLMENT_ENDPOINT,
            guid=guid,
            user_name=current_app.config['NYC_ID_USERNAME'],
            user_type=user_type
        )
        response = requests.put(
            urljoin(current_app.config['WEB_SERVICE_URL'],
                    ENROLLMENT_ENDPOINT),
            {
                "guid": guid,
                "userName": current_app.config['NYC_ID_USERNAME'],
                "userType": user_type,
                "signature": generate_signature(current_app.config['NYC_ID_PASSWORD'],
                                                string_to_sign)
            }
        )


# TODO: this
def unenroll():
    """
    Included for possible future use...

    """
    pass


def generate_string_to_sign(path, params, method='GET'):
    """
    Generate a string that can be signed to produce an
    authentication signature.

    :param path: path part of HTTP request URI
    :param method: HTTP method
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


def generate_signature(password, string):
    """
    Generate an authentication signature using HMAC-SHA1

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
        print("Failed to generate signature: ", e)
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
    :param ldap_server: LDAP Server Hostname / IP Address
    :param ldap_port: Port to use on LDAP server
    :param ldap_use_tls: Use a secure connection to the LDAP server
    :param ldap_cert_path: Certificate for Secure connection to LDAP
    :param ldap_sa_bind_dn: LDAP Bind Distinguished Name for Service Account
    :param ldap_sa_password: LDAP Service Account password
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
