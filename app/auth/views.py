"""
.. module:: auth.views.

   :synopsis: Handles SAML and LDAP authentication endpoints for NYC OpenRecords

"""
from datetime import datetime
from urllib.parse import urljoin

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import MobileApplicationClient

from flask import (
    request,
    redirect,
    session,
    render_template,
    url_for,
    abort,
    flash,
)
from flask_login import (
    login_user,
    logout_user,
    current_user,
    current_app
)
from app.auth import auth
from app.auth.forms import ManageUserAccountForm, LDAPLoginForm  # TODO: Manage Account
from app.auth.utils import (
    ldap_authentication,
    find_user_by_email,
    handle_user_data,
    revoke_and_remove_access_token,
)
from app.constants.web_services import USER_ENDPOINT, AUTH_ENDPOINT


@auth.route('/login', methods=['GET'])
def login():
    """
    If using LDAP, see ldap_login().

    If using SAML/OAuth, check for the presence of an access token
    in the session, which is used to fetch user information for processing.
    If no token exists, send the user to the authorization url
    (first leg of the OAuth 2 workflow).

    * NOTE *
    Since we are using OAuth Mobile Application Flow to fetch the information
    normally retrieved in a SAML Assertion, the url resulting from authorization
    is in the format 'redirect_uri#access_token=123guid=ABC...'. Notice the fragment
    identifier ('#') in place of what would normally be the '?'. Since Flask drops
    everything after the identifier, we must extract these values client-side in
    order to forward them to the server. Therefore, the redirect uri we are using
    is our home page (main.index) which detects the presence of an access token
    and redirects to the intended OAuth callback (auth.authorize).

    https://tools.ietf.org/html/rfc3986#section-3.5

    """
    return_to_url = request.args.get('return_to_url')  # TODO: Test with USE_OAUTH

    if current_app.config['USE_LDAP']:
        return redirect(url_for('auth.ldap_login', return_to_url=return_to_url))

    elif current_app.config['USE_OAUTH']:
        if session.get('token') is not None:
            oauth = OAuth2Session(
                client=MobileApplicationClient(client_id=current_app.config['CLIENT_ID']),
                token=session['token']
            )
            user_json = oauth.get(
                urljoin(current_app.config['WEB_SERVICES_URL'], USER_ENDPOINT)
            ).json()  # TODO: handle error (before attempting to get json?)
            return redirect(handle_user_data(
                user_json['guid'],
                user_json['userType'],
                user_json['email'],
                user_json.get('firstName'),
                user_json.get('middleInitial'),
                user_json.get('lastName'),
                user_json.get('validated'),
                user_json.get('termsOfUse'),
                return_to_url
            ))
        else:
            # redirect_uri = urljoin(request.host_url, url_for('main.index'))
            redirect_uri = 'https://openrecords-staging.appdev.records.nycnet/'
            if return_to_url:
                redirect_uri += '?return_to_url=' + return_to_url
            oauth = OAuth2Session(
                client=MobileApplicationClient(client_id=current_app.config['NYC_ID_USERNAME']),
                redirect_uri=redirect_uri
            )
            auth_url, _ = oauth.authorization_url(
                urljoin(current_app.config['WEB_SERVICES_URL'], AUTH_ENDPOINT)
            )
            return redirect(auth_url)
    return abort(404)


@auth.route('/authorize', methods=['GET'])
def authorize():
    """
    Store access token and a UTC timestamp for its
    expiration date and time in the session, then
    process SAML Assertion information.

    See: https://nyc4d.nycnet/nycidauthentication.shtml
    """
    session['token'] = {
        'access_token': request.args['access_token'],
        'token_type': request.args['token_type']
    }
    session['token_expires_at'] = datetime.utcnow().timestamp() + int(request.args['expires_in'])

    return redirect(handle_user_data(
        request.args['GUID'],
        request.args['userType'],
        request.args['mail'],
        request.args.get('givenName'),
        request.args.get('middleName'),
        request.args.get('sn'),
        request.args.get('nycExtTOUVersion'),
        request.args.get('nycExtEmailValidationFlag'),
        request.args.get('return_to_url')))


@auth.route('/logout', methods=['GET'])
def logout():
    timed_out = request.args.get('timeout')

    if current_app.config['USE_LDAP']:
        return redirect(url_for('auth.ldap_logout', timed_out=timed_out))

    elif current_app.config['USE_OAUTH']:
        if 'token' in session:
            revoke_and_remove_access_token()
        if timed_out is not None:
            flash("Your session timed out. Please login again", category='info')
        return redirect(url_for("main.index"))

    return abort(404)


# LDAP -----------------------------------------------------------------------------------------------------------------

@auth.route('/ldap_login', methods=['GET', 'POST'])
def ldap_login():
    login_form = LDAPLoginForm()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = find_user_by_email(email)

        if user is not None:
            authenticated = ldap_authentication(email, password)

            if authenticated:
                login_user(user)
                session.regenerate()  # KVSession.regenerate()
                session['user_id'] = current_user.get_id()

                return_to_url = request.form.get('return_to_url')
                url = return_to_url if return_to_url else url_for('main.index')

                return redirect(url)

            flash("Invalid username/password combination.", category="danger")
            return render_template('auth/ldap_login_form.html', login_form=login_form)
        else:
            flash("User not found. Please contact your agency FOIL Officer to gain access to the system.",
                  category="warning")
            return render_template('auth/ldap_login_form.html', login_form=login_form)

    elif request.method == 'GET':
        return render_template(
            'auth/ldap_login_form.html',
            login_form=login_form,
            return_to_url=request.args.get('return_to_url', ''))


@auth.route('/ldap_logout', methods=['GET'])
def ldap_logout(timed_out=None):
    logout_user()
    session.regenerate()
    if timed_out is not None:
        flash("Your session timed out. Please login again", category='info')
    return redirect(url_for('main.index'))
