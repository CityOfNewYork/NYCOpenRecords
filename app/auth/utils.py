import json
from urllib.parse import urljoin, urlparse

from flask import current_app, request, session
from onelogin.saml2.auth import OneLogin_Saml2_Auth

from app.constants import (
    AGENCY_USER
)
from app.db_utils import create_object, update_object
from app.models import Agency, User


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


def process_user_data(guid, title=None, organization=None, phone=None, fax=None, mailing_address=None):
    """
    Processes user data for a logged in user. Will update the database with user parameters, or create a user entry
    in the database if none exists.

    :param guid: Unique ID for the user; String
    :param title: User's title; String
    :param organization: Users organization; String
    :param phone: User's phone number; String
    :param fax: User's fax number; String
    :param mailing_address: User's mailing address; JSON Object
    :return: User GUID + User Type
    """
    user = User.query.filter_by(guid=guid).first()

    if user:
        if user.user_type == AGENCY_USER:
            organization = Agency.query.filter_by(email_domain=user.email.split('@')[-1]).first()

        user_id = update_user(
            guid=guid,
            agency=(organization.ein or None),
            title=title,
            organization=organization.name,
            phone=phone,
            fax=fax,
            mailing_address=mailing_address
        )
    else:
        user_type = session['samlUserdata']['userType'][0]

        if user_type == AGENCY_USER:
            organization = Agency.query.filter_by(email_domain=user.email.split('@')[-1]).first()
        try:
            email = session['samlUserdata']['mail'][0]
        except KeyError:
            email = None

        try:
            first_name = session['samlUserdata']['givenName'][0]
        except KeyError:
            first_name = None

        try:
            middle_initial = session['samlUserdata']['middleName'][0]
        except KeyError:
            middle_initial = None

        try:
            last_name = session['samlUserdata']['sn'][0]
        except KeyError:
            last_name = None

        try:
            email_validated = session['samlUserdata']['nycExtEmailValidationFlag'][0]
        except KeyError:
            email_validated = None

        try:
            terms_of_use_accepted = session['samlUserdata']['nycExtTOUVersion'][0]
        except KeyError:
            terms_of_use_accepted = None

        user_id = User(
            guid=guid,
            user_type=user_type,
            agency=(organization.ein or None),
            email=email,
            first_name=first_name,
            middle_initial=middle_initial,
            last_name=last_name,
            email_validated=email_validated,
            terms_of_user_accepted=terms_of_use_accepted,
            title=title,
            organization=organization.name,
            phone=phone,
            fax=fax,
            mailing_address=user
        )
        create_object(user)
    return user_id


def create_mailing_address(address_one, city, state, zipcode, address_two=None):
    """
    Creates a JSON object from the parts of a mailing address for a user.

    :param address_one: Line one of the user's address; String
    :param city: City of the user's address; String
    :param state: State of the user's address; String
    :param zipcode: Zip code of the user; 5 Digit integer
    :param address_two: Optional line two of the user's address; String
    :return: JSON Object containing the address
    """
    mailing_address = {
        'address_one': address_one,
        'address_two': address_two,
        'city': city,
        'state': state,
        'zip': zipcode
    }
    mailing_address = json.dumps(mailing_address)

    return mailing_address


def update_user(guid=None, **kwargs):
    """
    Updates a user if they exist in the database.
    :param guid:
    :param kwargs: Fields that need to be updated in the user.
    :return: GUID + UserType of the user (forms unique ID)
    """
    user = str()
    if not guid:
        return None
    for key, value in kwargs.items():
        user = update_object(attribute=key, value=value, obj_type="User", obj_id=guid)

    if not user:
        return None
    return user
