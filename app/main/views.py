"""
.. module:: main.views.

   :synopsis: Handles all core URL endpoints for the timeclock application
"""
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from app.constants import OPENRECORDS_DL_EMAIL
from app.constants.response_privacy import PRIVATE
from app.lib.db_utils import create_object, update_object
from app.lib.email_utils import send_contact_email
from app.models import Emails, Users
from app.request.forms import TechnicalSupportForm
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    fresh_login = request.args.get('fresh_login', False)
    verify_mfa = request.args.get('verify_mfa', False)
    if current_user.is_authenticated:
        if verify_mfa:
            if current_user.has_mfa:
                return redirect(url_for('mfa.verify'))
            else:
                return redirect(url_for('mfa.register'))
        if fresh_login:
            if current_user.session_id is not None:
                return render_template('main/home.html', duplicate_session=True)
            update_object(
                {
                    'session_id': session.sid
                },
                Users,
                current_user.guid
            )
    return render_template('main/home.html')


@main.route('/index.html', methods=['GET'])
@main.route('/status', methods=['GET'])
def status():
    return '', 200


@main.route('/contact', methods=['GET', 'POST'])
@main.route('/technical-support', methods=['GET', 'POST'])
def technical_support():
    form = TechnicalSupportForm()

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if all((name, email, subject, message)):
            body = "Name: {}\n\nEmail: {}\n\nSubject: {}\n\nMessage:\n{}".format(
                name, email, subject, message)
            create_object(
                Emails(
                    request_id=None,
                    privacy=PRIVATE,
                    to=OPENRECORDS_DL_EMAIL,
                    cc=None,
                    bcc=None,
                    subject=subject,
                    body=body,
                )
            )
            if current_user.is_agency:
                send_contact_email(subject, [current_app.config['OPENRECORDS_AGENCY_SUPPORT_DL']], body, email)
            else:
                send_contact_email(subject, [OPENRECORDS_DL_EMAIL], body, email)
            flash('Your message has been sent. We will get back to you.', category='success')
        else:
            flash('Cannot send email.', category='danger')
    error_id = request.args.get('error_id', '')
    return render_template('main/contact.html', error_id=error_id, form=form)


@main.route('/faq', methods=['GET'])
def faq():
    return render_template('main/faq.html')


@main.route('/about', methods=['GET'])
def about():
    return render_template('main/about.html')


@main.route('/active', methods=['POST'])
def active():
    """
    Extends a user's session.
    :return:
    """
    session.modified = True
    return 'OK'
