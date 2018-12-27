"""
.. module:: auth.views.

   :synopsis: Handles OAUTH and LDAP authentication endpoints for NYC OpenRecords

"""

from flask import (
    abort, flash, make_response, redirect, render_template, request, session, url_for
)
from flask_login import (
    current_app, current_user, login_required, login_user, logout_user
)

from app import csrf
from app.auth import auth
from app.auth.constants.error_msg import UNSAFE_NEXT_URL
from app.auth.forms import LDAPLoginForm, ManageAgencyUserAccountForm, ManageUserAccountForm
from app.auth.utils import (
    find_user_by_email, init_saml_auth, is_safe_url,
    ldap_authentication, prepare_onelogin_request, saml_acs,
    saml_slo, saml_sls, update_openrecords_user
)


@auth.route('/saml', methods=['GET', 'POST'])
@csrf.exempt
def saml():
    """
    View function to handle SAML SSO Workflow.

    GET Parameters:
        sso - Handle a regular login request (user clicks Login in the navbar)
        sso2 - Handle a login request from the application (user attempts to access a privileged resource)
        acs - Handle a login response from the IdP and return the user to the provided redirect URL (defaults to the home page)
        slo - Generate a Logout request for the IdP
        sls - Handle a Logout Response from the IdP and destroy the local session

    """
    # 1. Convert Flask Request object to OneLogin Request Dictionary
    onelogin_request = prepare_onelogin_request(request)

    # 2. Create OneLogin Object to handle SAML Workflow
    onelogin_saml_auth = init_saml_auth(onelogin_request)

    # 3. Handle request based on GET parameter.
    if 'sso' in request.args or len(request.args) == 0:
        return redirect(onelogin_saml_auth.login())
    elif 'sso2' in request.args:
        return_to = '%sattrs/' % request.host_url
        return redirect(onelogin_saml_auth.login(return_to))
    elif 'acs' in request.args:
        return saml_acs(onelogin_saml_auth, onelogin_request)
    elif 'slo' in request.args:
        return redirect(saml_slo(onelogin_saml_auth))
    elif 'sls' in request.args:
        return saml_sls(onelogin_saml_auth)
    else:
        flash('Oops! Something went wrong. Please try to perform your action again later.', category="warning")
        return redirect(url_for('main.index'))


@auth.route('/login', methods=['GET'])
def login():
    """
    Based off of: https://flask-login.readthedocs.io/en/latest/#login-example
    If using LDAP, see ldap_login().
    If using SAML/OAuth, check for the presence of an access token
    in the session, which is used to fetch user information for processing.
    If no token exists, send the user to the authorization url
    (first leg of the OAuth 2 workflow).
    * NOTE *
    Since we are using OAuth Mobile Application Flow to fetch the information
    normally retrieved in a SAML Assertion, the url resulting from authorization
    is in the format 'redirect_uri#access_token=123guid=ABC...'. Notice the fragment
    identifier ('#') in place of what would normally be the '?' separator.
    Since Flask drops everything after the identifier, we must extract these values
    client-side in order to forward them to the server. Therefore, the redirect uri
    we are using is our home page (main.index, along with the 'next' url if present)
    which contains a script that detects the presence of an access token
    and redirects to the intended OAuth callback (auth.authorize).
    https://tools.ietf.org/html/rfc3986#section-3.5
    """
    next_url = request.args.get('next')

    if not current_app.config['USE_LDAP'] and not current_app.config['USE_OAUTH']:
        login_form = LDAPLoginForm()
        if request.method == 'POST':
            email = request.form['email']

            user = find_user_by_email(email)

            if user is not None:
                authenticated = True

                if authenticated:
                    login_user(user)
                    session.regenerate()
                    session['user_id'] = current_user.get_id()

                    next_url = request.form.get('next')
                    if not is_safe_url(next_url):
                        return abort(400, UNSAFE_NEXT_URL)

                    return redirect(next_url or url_for('main.index'))

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
                next_url=request.args.get('next', ''))

    if current_app.config['USE_LDAP']:
        return redirect(url_for('auth.ldap_login', next=next_url))

    if current_app.config['USE_SAML']:
        if next_url:
            return redirect(url_for('auth.saml', sso2=next))

    return abort(404)


@auth.route('/logout', methods=['GET'])
def logout():
    """Unified logout endpoint for all authentication types.

    GET Args:
        timeout (bool): If True, logout is being called due to a session timeout.
        forced_logout (bool): If True, logout is being called due to a duplicate session.

    Returns:
        Redirect to the appropriate logout endpoint.
    """
    timeout = request.args.get('timeout', False)
    forced_logout = request.args.get('forced_logout', False)

    if current_app.config['USE_LDAP']:
        return redirect(url_for('auth.ldap_logout', timeout=timeout, forced_logout=forced_logout))

    elif current_app.config['USE_OAUTH']:
        return redirect(url_for('auth.oauth_logout', timeout=timeout, forced_logout=forced_logout))

    if current_app.config['USE_SAML']:
        return redirect(url_for('auth.saml', slo='true', timeout=timeout, forced_logout=forced_logout))

    return abort(404)


@auth.route('/metadata/', methods=['GET'])
def metadata():
    req = prepare_onelogin_request(request)
    saml_auth = init_saml_auth(req)
    settings = saml_auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
    else:
        resp = make_response(', '.join(errors), 500)
    return resp


@auth.route('/manage', methods=['GET', 'POST'])
@login_required
def manage():
    if current_user.is_agency:
        form = ManageAgencyUserAccountForm(user=current_user)
    else:
        form = ManageUserAccountForm(user=current_user)

    if request.method == 'POST':
        if form.validate_on_submit():
            update_openrecords_user(form)
            redirect(url_for('auth.manage'))
        else:
            flash("Account cannot be updated.", category="danger")
            return render_template('auth/manage_account.html', form=form)
    else:
        form.autofill()

    return render_template('auth/manage_account.html', form=form, is_agency=current_user.is_agency)


# LDAP -----------------------------------------------------------------------------------------------------------------

@auth.route('/ldap_login', methods=['GET', 'POST'])
def ldap_login():
    if not current_app.config['USE_LDAP']:
        return redirect(url_for('auth.login'))
    login_form = LDAPLoginForm()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = find_user_by_email(email)

        if user is not None:
            authenticated = ldap_authentication(email, password)

            if authenticated:
                login_user(user)
                session.regenerate()
                session['user_id'] = current_user.get_id()

                next_url = request.form.get('next')
                if not is_safe_url(next_url):
                    return abort(400, UNSAFE_NEXT_URL)

                return redirect(next_url or url_for('main.index'))

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
            next_url=request.args.get('next', ''))


@auth.route('/ldap_logout', methods=['GET'])
def ldap_logout(timed_out=False, forced_logout=False):
    logout_user()
    session.destroy()
    if timed_out:
        flash("Your session timed out. Please login again", category='info')
    return redirect(url_for('main.index'))