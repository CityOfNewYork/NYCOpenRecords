from flask import Flask, render_template, session, redirect, url_for, current_app, request, Response
from . import auth
from .forms import LoginForm
from .. import app


@auth.route('/login', methods=['GET'])
def login_form():
    '''
    Generates the login page
    :return: login.html
    '''
    app.logger.info("def login_form")
    #Check to make sure if the login form is being accessed from the agency side of hte application
    if request.host_url.split('//')[1] != app.config['AGENCY_APPLICATION_URL'].split('//')[1]:
        return redirect(url_for('index'))
    user_id = get_user_id()

@auth.route('/login', methods=['POST'])
def login():
    '''
    Takes in a username and password and authenticates the user.
    :return: login.html
    '''
    auth.logger.info("def login():")
    form = LoginForm()
    errors = []
    if request.method == 'POST':
        if (form.username.data is not None and form.username.data != '') and (
                        form.password.data is not None and form.password.data != ''):
            user_to_login = authenticate_login(form.username.data, form.password.data)
            if user_to_login:
                app.logger.info("\n\nSuccessful login for \nemail : %s " % form.username.data)
                login_user(user_to_login)
                session.regenerate()
                session.pop("_csrf_token", None)
                session.pop('_id', None)
                session['username'] = form.username.data
                redirect_url = get_redirect_target()
                if 'login' in redirect_url or 'logout' in redirect_url:
                    return redirect(url_for('display_all_requests', _scheme='https', _external=True))
                else:
                    if 'city' not in redirect_url:
                        redirect_url = redirect_url.replace("/request", "/city/request")
                    return redirect(redirect_url)
            else:
                auth.logger.info(
                    "\n\nLogin failed (due to incorrect email/password combo) for \nemail : %s " % form.username.data)
                errors.append('Incorrect email/password combination. Please try again. If you forgot your password, '
                              'please contact your agency IT Department.')
                return render_template('login.html', form=form, errors=errors)
        else:
            errors.append('Something went wrong')
            return render_template('login.html', form=form, errors=errors)
    elif request.method == 'GET':
        if request.host_url.split('//')[1] != app.config['AGENCY_APPLICATION_URL'].split('//')[1]:
            return redirect(url_for('landing'))
        user_id = get_user_id()
        if user_id:
            redirect_url = get_redirect_target()
            return redirect(redirect_url)
        else:
            return render_template('login.html', form=form)
    else:
        return bad_request(400)
