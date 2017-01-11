"""
.. module:: main.views.

   :synopsis: Handles all core URL endpoints for the timeclock application
"""
from . import main
from flask import (
    render_template,
    flash,
    request,
    session
)
from app.lib.email_utils import send_contact_email
from app.lib.db_utils import create_object
from app.models import Emails
from app.constants import OPENRECORDS_DL_EMAIL
from app.constants.response_privacy import PRIVATE


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('main/home.html')


@main.route('/index.html', methods=['GET'])
def status():
    return 200


@main.route('/contact', methods=['GET', 'POST'])
def contact():
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
            send_contact_email(subject, body, email)
            flash('Your message has been sent. We will get back to you.', category='success')
        else:
            flash('Cannot send email.', category='danger')
    return render_template('main/contact.html')


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