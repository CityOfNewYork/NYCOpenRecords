"""
.. module:: auth.views.

   :synopsis: Handles SAML and LDAP authentication endpoints for NYC OpenRecords
"""

from flask import (
    request,
    redirect,
    session,
    render_template,
    make_response,
    url_for,
    abort,
    flash
)
from flask_login import (
    login_user,
    logout_user,
    current_user,
    current_app
)
from ast import literal_eval

from app.auth import auth
from app.auth.forms import ManageUserAccountForm, LDAPLoginForm
from app.auth.utils import (
    prepare_flask_request,
    init_saml_auth,
    process_user_data,
    find_or_create_user,
    ldap_authentication,
    find_user
)
from app.lib.user_information import create_mailing_address

from app.lib.onelogin.saml2.utils import OneLogin_Saml2_Utils


@auth.route('/login', methods=['GET'])
def login():
    return_to_url = request.args.get('return_to_url')
    if current_app.config['USE_LDAP']:
        return redirect(url_for('auth.ldap_login', return_to_url=return_to_url))
    elif current_app.config['USE_SAML']:
        return redirect(url_for('auth.saml'))

    return abort(404)


@auth.route('/logout', methods=['GET'])
def logout():
    timed_out = request.args.get('timeout')
    if current_app.config['USE_LDAP']:
        return redirect(url_for('auth.ldap_logout', timed_out=timed_out))
    elif current_app.config['USE_SAML']:
        # return redirect(url_for('auth.saml'), timed_out=timed_out)
        return abort(404)

    return abort(404)


@auth.route('/ldap_login', methods=['GET', 'POST'])
def ldap_login():
    login_form = LDAPLoginForm()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = find_user(email)

        if user is not None:
            authenticated = ldap_authentication(email, password)

            if authenticated:
                login_user(user)
                session['user_id'] = current_user.get_id()

                return_to_url = request.form.get('return_to_url', None)
                url = return_to_url if return_to_url is not None else url_for('main.index')

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
    if timed_out is not None:
        flash("Your session timed out. Please login again", category='info')
    return redirect(url_for('main.index'))
