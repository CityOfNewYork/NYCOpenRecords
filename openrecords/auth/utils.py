from urllib import parse
from urllib.parse import urljoin, urlparse

from flask import request
from flask_login import current_user
from onelogin.saml2.auth import OneLogin_Saml2_Auth

from .. import app


def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(req, custom_base_path=app.config['SAML_PATH'])
    return auth


def get_user_id():
    if current_user.is_authenticated:
        return current_user.id
    return None


def get_redirect_target():
    """ Taken from http://flask.pocoo.org/snippets/62/ """
    app.logger.info("def get_redirect_target():")
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


def is_safe_url(target):
    """ Taken from http://flask.pocoo.org/snippets/62/ """
    app.logger.info("def is_safe_url(target):")
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def prepare_flask_request(request):
    """
    If server is behind proxys or balancers use the HTTP_X_FORWARDED fields, create a Flask request
    :param request:
    :return:
    """
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
