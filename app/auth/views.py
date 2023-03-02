"""
.. module:: auth.views.

   :synopsis: Handles authentication endpoints for NYC OpenRecords

"""

from flask import (
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from app import csrf
from app.auth import auth
from app.auth.constants.error_msg import UNSAFE_NEXT_URL
from app.auth.forms import (
    BasicLoginForm,
    ManageAgencyUserAccountForm,
    ManageUserAccountForm,
)
from app.auth.utils import (
    find_user_by_email,
    init_saml_auth,
    is_safe_url,
    ldap_authentication,
    prepare_onelogin_request,
    saml_acs,
    saml_slo,
    saml_sls,
    update_openrecords_user,
    create_auth_event
)
from app.constants import event_type


@auth.route("/login", methods=["GET"])
def login():
    """Handle login redirects for users.

    This application supports three methods for login: SAML 2.0, LDAP, and Local Authentication

    SAML 2.0 integrates with the City of New York Authentication System (NYC.ID). Users will be redirected to the SAML
    authentication endpoint. Please see app.auth.saml for details.

    LDAP authentication will redirect the user to a Flask login form and authenticate them using the LDAP protocol.
    Please see app.auth.ldap_login for details.

    Local Auth is used for development and testing purposes only. It allows a user to login using any password, as long
    as the email is valid and in the database.

    The three methods are called in the preferred method for authentication: 1) SAML 2) LDAP 3) Local Auth

    Based off of: https://flask-login.readthedocs.io/en/latest/#login-example

    Args:
        next (str): URL to send the user to after successful authentication.

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Response redirecting the browser to the proper URL for login
    """
    next_url = request.form.get("next", None)

    if current_app.config["USE_SAML"]:
        if next_url:
            return redirect(url_for("auth.saml", sso2=next_url))
        return redirect(url_for("auth.saml", sso=None))

    elif current_app.config["USE_LDAP"]:
        return redirect(url_for("auth.ldap_login", next=next_url))

    elif current_app.config["USE_LOCAL_AUTH"]:
        return redirect(url_for("auth.local_login", nex=next_url))

    return abort(404)


@auth.route("/logout", methods=["GET"])
def logout():
    """
    Unified logout endpoint for all authentication types.

    GET Args:
        timeout (bool): If True, logout is being called due to a session timeout.
        forced_logout (bool): If True, logout is being called due to a duplicate session.

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Redirect to the appropriate logout endpoint.
    """
    timeout = request.args.get("timeout", False)
    forced_logout = request.args.get("forced_logout", False)

    if current_app.config["USE_LDAP"]:
        return redirect(
            url_for("auth.ldap_logout", timeout=timeout, forced_logout=forced_logout)
        )

    elif current_app.config["USE_SAML"]:
        return redirect(
            url_for(
                "auth.saml", slo="true", timeout=timeout, forced_logout=forced_logout
            )
        )

    elif current_app.config["USE_LOCAL_AUTH"]:
        logout_user()
        session.clear()
        if timeout:
            flash("Your session timed out. Please login again", category="info")
        return redirect(url_for("main.index"))

    return abort(404)


@auth.route("/manage", methods=["GET", "POST"])
@login_required
def manage():
    """
    Allow users to manage their OpenRecords specific attributes.

    For POST requests, updates the users data in the database.
    For GET requests, pulls the current user data from the database and pre-populates the form.

    Requires users to have an active authentication session.

    Returns:
        Flask Response with Manage Page

    """
    if current_user.is_agency:
        form = ManageAgencyUserAccountForm(user=current_user)
    else:
        form = ManageUserAccountForm(user=current_user)

    if request.method == "POST":
        if form.validate_on_submit():
            update_openrecords_user(form)
            redirect(url_for("auth.manage"))
        else:
            flash("Account cannot be updated.", category="danger")
            return render_template("auth/manage_account.html", form=form)
    else:
        form.autofill()

    return render_template(
        "auth/manage_account.html", form=form, is_agency=current_user.is_agency
    )


# SAML Authentication Endpoints
@auth.route("/saml", methods=["GET", "POST"])
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

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Redirects the user to the proper location in the SAML Auth Workflow.

    """
    if not current_app.config['USE_SAML']:
        return redirect(url_for('auth.login'))

    # 1. Convert Flask Request object to OneLogin Request Dictionary
    onelogin_request = prepare_onelogin_request(request)

    # 2. Create OneLogin Object to handle SAML Workflow
    onelogin_saml_auth = init_saml_auth(onelogin_request)

    # 3. Handle request based on GET parameter.
    if "sso" in request.args or len(request.args) == 0:
        return redirect(onelogin_saml_auth.login())
    elif "sso2" in request.args:
        return_to = "{host_url}{endpoint}".format(
            host_url=request.host_url, endpoint=request.args.get("sso2", "/")[1:]
        )
        return redirect(onelogin_saml_auth.login(return_to))
    elif "acs" in request.args:
        return saml_acs(onelogin_saml_auth, onelogin_request)
    elif "slo" in request.args:
        return redirect(saml_slo(onelogin_saml_auth))
    elif "sls" in request.args:
        user_guid = current_user.guid if not current_user.is_anonymous else None
        return saml_sls(onelogin_saml_auth, user_guid)
    else:
        flash(
            "Oops! Something went wrong. Please try to perform your action again later.",
            category="warning",
        )
        return redirect(url_for("main.index"))


@auth.route("/metadata/", methods=["GET"])
def metadata():
    """
    Access the SAML SP metadata for this application

    Returns:
        HTTP Response (werkzeug.wrappers.Response): XML SP Metadata
    """
    req = prepare_onelogin_request(request)
    saml_auth = init_saml_auth(req)
    settings = saml_auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers["Content-Type"] = "text/xml"
    else:
        resp = make_response(", ".join(errors), 500)
    return resp


# LDAP Authentication Endpoints
@auth.route("/ldap_login", methods=["GET", "POST"])
def ldap_login():
    """
    Login a user using the LDAP protocol

    Args:
        next (str): URL to redirect the user to if login is successful. (in request.args)

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Redirects the user to the home page (if successful) or to the
                                                    login page again (if unsuccessful)

    """
    if not current_app.config["USE_LDAP"]:
        return redirect(url_for("auth.login"))
    login_form = BasicLoginForm()
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = find_user_by_email(email)

        if user is not None:
            authenticated = ldap_authentication(email, password)

            if authenticated:
                login_user(user)
                session["user_id"] = current_user.get_id()

                create_auth_event(
                    auth_event_type=event_type.USER_LOGIN,
                    user_guid=session["user_id"],
                    new_value={
                        'success': True,
                        'type': current_app.config['AUTH_TYPE']
                    }
                )

                next_url = request.form.get("next", None)
                if not is_safe_url(next_url) or next_url is None:
                    return abort(400, UNSAFE_NEXT_URL)

                return redirect(next_url or url_for("main.index"))
            error_message = "Invalid username/password combination."
            create_auth_event(
                auth_event_type=event_type.USER_FAILED_LOG_IN,
                user_guid=session["user_id"],
                new_value={
                    'success': False,
                    'type': current_app.config['AUTH_TYPE'],
                    'message': error_message
                }
            )
            flash(error_message, category="danger")
            return render_template("auth/ldap_login_form.html", login_form=login_form)
        else:
            error_message = "User not found. Please contact your agency FOIL Officer to gain access to the system."
            create_auth_event(
                auth_event_type=event_type.USER_FAILED_LOG_IN,
                user_guid=session["user_id"],
                new_value={
                    'success': False,
                    'type': current_app.config['AUTH_TYPE'],
                    'message': error_message
                }
            )
            flash(error_message, category="warning")
            return render_template("auth/ldap_login_form.html", login_form=login_form)

    elif request.method == "GET":
        return render_template(
            "auth/ldap_login_form.html",
            login_form=login_form,
            next_url=request.args.get("next", ""),
        )


@auth.route("/ldap_logout", methods=["GET"])
def ldap_logout():
    """
    Log a user out from the LDAP server.
    Args:
        timed_out (bool): If True, the users client side session timed-out.

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Redirects the user to the home page

    """
    timed_out = request.args.get('timed_out', False)
    logout_user()
    create_auth_event(
        auth_event_type=event_type.USER_FAILED_LOG_IN,
        user_guid=session["user_id"],
        new_value={
            'success': True,
            'type': current_app.config['AUTH_TYPE'],
            'timed_out': timed_out
        }
    )
    session.clear()
    if timed_out:
        flash("Your session timed out. Please login again", category="info")
    return redirect(url_for("main.index"))


# Local Authentication Endpoints
@auth.route('/local_login', methods=['GET', 'POST'])
def local_login():
    """
    Authenticate a user against the database (ignore password).

    Allows developers to test functionality as valid users without needing to use a third party service.

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Redirects the user to the home page (if successful) or to the
                                                    login page again (if unsuccessful)
    """
    if not current_app.config["USE_LOCAL_AUTH"]:
        return redirect(url_for('auth.login'))
    login_form = BasicLoginForm()
    if request.method == "POST":
        email = request.form["email"]

        user = find_user_by_email(email)

        if user is not None:
            login_user(user)
            session["user_id"] = current_user.get_id()

            create_auth_event(
                auth_event_type=event_type.USER_LOGIN,
                user_guid=session["user_id"],
                new_value={
                    'success': True,
                }
            )

            next_url = request.form.get("next")
            if not is_safe_url(next_url):
                return abort(400, UNSAFE_NEXT_URL)

            return redirect(next_url or url_for("main.index"))
        else:
            error_message = "User {email} not found. Please contact your agency FOIL Officer to gain access to the system.".format(
                email=email)
            flash(error_message, category="warning")
            return render_template(
                "auth/local_login_form.html", login_form=login_form
            )

    elif request.method == "GET":
        return render_template(
            "auth/local_login_form.html",
            login_form=login_form,
            next_url=request.args.get("next", ""),
        )


@auth.route("/local_logout", methods=["GET"])
def local_logout(timed_out=False):
    """
    Log a user out from the server.
    Args:
        timed_out (bool): If True, the users client side session timed-out.

    Returns:
        HTTP Response (werkzeug.wrappers.Response): Redirects the user to the home page
    """
    logout_user()
    create_auth_event(
        auth_event_type=event_type.USER_FAILED_LOG_IN,
        user_guid=session["user_id"],
        new_value={
            'success': True,
            'type': current_app.config['AUTH_TYPE']
        }
    )
    session.clear()
    if timed_out:
        flash("Your session timed out. Please login again", category="info")
    return redirect(url_for("main.index"))
