"""
.. module:: auth.views.

   :synopsis: Authentication utilities for NYC OpenRecords
"""
import ssl

from urllib.parse import urljoin, urlparse

from flask import current_app, request, session
from app.lib.onelogin.saml2.auth import OneLogin_Saml2_Auth
from app import login_manager
from app.constants import USER_ID_DELIMITER
from app.lib.db_utils import create_object, update_object
from app.models import Agencies, Users

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


def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(req, custom_base_path=current_app.config['SAML_PATH'])
    return auth


def get_redirect_target():
    """ Taken from http://flask.pocoo.org/snippets/62/ """
    current_app.logger.info("def get_redirect_target():")
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


def is_safe_url(target):
    """ Taken from http://flask.pocoo.org/snippets/62/ """
    current_app.logger.info("def is_safe_url(target):")
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def prepare_flask_request(request):
    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    url_data = urlparse(request.url)
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        # Uncomment if using ADFS as IdP, https://github.com/onelogin/python-saml/pull/144
        # 'lowercase_urlencoding': True,
        'post_data': request.form.copy()
    }


def process_user_data(guid, title=None, organization=None, phone_number=None, fax_number=None, mailing_address=None):
    """
    Processes user data for a logged in user. Will update the database with user parameters, or create a user entry
    in the database if none exists.

    :param guid: Unique ID for the user; String
    :param title: User's title; String
    :param organization: Users organization; String
    :param phone_number: User's phone_number number; String
    :param fax_number: User's fax_number number; String
    :param mailing_address: User's mailing address; JSON Object
    :return: User GUID + User Type
    """
    user = Users.query.filter_by(guid=guid).first()

    if user:
        if user.is_agency_user:
            organization = Agencies.query.filter_by(email_domain=user.email.split('@')[-1]).first()

            user = update_user(
                guid=guid,
                auth_user_type=user.auth_user_type,
                agency=(organization.ein or None),
                title=title,
                organization=organization.name,
                phone_number=phone_number,
                fax_number=fax_number,
                mailing_address=mailing_address
            )
        else:
            user = update_user(
                guid=guid,
                auth_user_type=user.auth_user_type,
                title=title,
                organization=organization,
                phone_number=phone_number,
                fax_number=fax_number,
                mailing_address=mailing_address
            )

    else:
        user = create_user(title=None, organization=None, phone_number=None, fax_number=None, mailing_address=None)
    return user


def update_user(guid=None, auth_user_type=None, **kwargs):
    """
    Updates a user if they exist in the database.
    :param guid:
    :param kwargs: Fields that need to be updated in the user.
    :return: GUID + UserType of the user (forms unique ID)
    """
    user = str()
    if not guid:
        return None

    user = update_object(kwargs, Users, obj_id=(guid, auth_user_type))

    if not user:
        return None
    return user


def find_or_create_user(guid, auth_user_type):
    """
    Given a guid and auth_user_type, equivalent to a user id, find or create a user in the database.

    Returns the User object and a boolean marking the user as a new user.

    :param unicode guid: GUID for the user
    :param unicode auth_user_type: User Type. See auth.constants for list of valid user types
    :return: (User Object, Boolean for Is new User)
    """
    user = Users.query.filter_by(guid=str(guid[0]), auth_user_type=str(auth_user_type[0])).first()

    if user:
        return user, False
    else:
        user = create_user()
        return user, True


def create_user(title=None, organization=None, phone_number=None, fax_number=None, mailing_address=None):
    """

    :return:
    """
    saml_user_data = session['samlUserdata']

    guid = saml_user_data['GUID'][0]

    auth_user_type = saml_user_data['userType'][0]

    # Determine if the user's email address has been validated
    # nycExtEmailValidationFlag is empty if auth_user_type = Saml2In:NYC Employees
    # Otherwise, the validation flag will be either TRUE or FALSE
    if saml_user_data.get('nycExtEmailValidationFlag', None):
        if len(saml_user_data.get('nycExtEmailValidationFlag')[0]) == 0:
            email_validated = False
        else:
            email_validated = saml_user_data.get('nycExtEmailValidationFlag')[0]
            if email_validated == 'TRUE':
                email_validated = True
            else:
                email_validated = False
    else:
        email_validated = False

    # Get the user's email (mail), if provided, otherwise email will be an empty string
    if saml_user_data.get('mail', None):
        if len(saml_user_data.get('mail')) == 0:
            email = ''
        else:
            email = saml_user_data.get('mail')[0]
    else:
        email = ''

    # Get the users first_name, if provided, otherwise first_name will be an empty string
    if saml_user_data.get('givenName', None):
        if len(saml_user_data.get('givenName')) == 0:
            first_name = ''
        else:
            first_name = saml_user_data.get('givenName')[0]
    else:
        first_name = ''

    # Get the user's middle_initial (middleName), if provided, otherwise middle_initial will be an empty string
    if saml_user_data.get('middleName', None):
        if len(saml_user_data.get('middleName')) == 0:
            middle_initial = ''
        else:
            middle_initial = saml_user_data.get('middleName')[0]
    else:
        middle_initial = ''

    # Get the user's last_name (sn), if provided, otherwise last_name will be an empty string
    if saml_user_data.get('sn', None):
        if len(saml_user_data.get('sn')) == 0:
            last_name = ''
        else:
            last_name = saml_user_data.get('sn')[0]
    else:
        last_name = ''

    # Get the user's last_name (sn), if provided, otherwise last_name will be an empty string
    if saml_user_data.get('nycExtTOUVersion', None):
        if len(saml_user_data.get('nycExtTOUVersion')) == 0:
            terms_of_use_accepted = None
        else:
            terms_of_use_accepted = saml_user_data.get('nycExtTOUVersion')[0]
    else:
        terms_of_use_accepted = None

    user = Users(guid=guid,
                 auth_user_type=auth_user_type,
                 email=email,
                 first_name=first_name,
                 middle_initial=middle_initial,
                 last_name=last_name,
                 email_validated=email_validated,
                 terms_of_use_accepted=terms_of_use_accepted,
                 title=title,
                 organization=organization,
                 phone_number=phone_number,
                 fax_number=fax_number,
                 mailing_address=mailing_address)

    if create_object(user):
        return user
    else:  # Insert Error Message
        return None


def find_user(email):
    """
    Find a user by email address in the database. Used for LDAP Authentication ONLY.
    :param email: Email address
    :return: User object.
    """
    return Users.query.filter_by(email=email, is_agency_active=True).first()


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
