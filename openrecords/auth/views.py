from flask import Flask, render_template, session, redirect, url_for, current_app, request, Response
from flask_login import current_user, login_user
from urllib import parse
from urllib.parse import urljoin
from . import auth
from .forms import LoginForm
from .. import app
from .. utils import authenticate_login

def get_user_id():
    if current_user.is_authenticated:
        return current_user.id
    return None

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
    ref_url = parse(request.host_url)
    test_url = parse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@app.route("/<page>")
def any_page(page):
    app.logger.info("def any_page(page):")
    try:
        return render_template('%s.html' % (page))
    except:
        return page_not_found(404)


@app.errorhandler(400)
def bad_request(e):
    app.logger.info("def bad_request(e):")
    return render_template("400.html"), 400


@app.errorhandler(401)
def unauthorized(e):
    app.logger.info("def unauthorized(e):")
    return render_template("401.html"), 401


@app.errorhandler(403)
def access_denied(e):
    app.logger.info("def access_denied(e):")
    return redirect(url_for('login'))


@app.errorhandler(404)
def page_not_found(e):
    app.logger.info("def page_not_found(e):")
    return render_template("404.html"), 404


@app.errorhandler(405)
def method_not_allowed(e):
    app.logger.info("def method_not_allowed(e):")
    return render_template("405.html"), 405


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.info("def internal_server_error(e):")
    return render_template("500.html"), 500


@app.errorhandler(501)
def unexplained_error(e):
    app.logger.info("def unexplained_error(e):")
    return render_template("501.html"), 501


@app.errorhandler(502)
def bad_gateway(e):
    app.logger.info("def bad_gateway(e):")
    render_template("500.html"), 502


@app.errorhandler(503)
def service_unavailable(e):
    app.logger.info("def service_unavailable(e):")
    render_template("500.html"), 503
