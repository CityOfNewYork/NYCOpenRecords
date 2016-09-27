"""
.. module:: main.views.

   :synopsis: Handles all core URL endpoints for the timeclock application
"""

from datetime import datetime
from flask import current_app
from flask import (
    render_template,
    flash,
    request,
    make_response,
    url_for,
    redirect,
    session
)
from flask_mail import Message
from app.email_utils import send_email
from flask_wtf import Form
from wtforms import SubmitField
from app.constants import TEST_EMAIL, TEST_CC, TEST_BCC, TEST_SUBJECT

from app.models import Users
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('base.html')


class EmailForm(Form):
    submit = SubmitField('Send Email')


# Used for testing email functionality
@main.route('/email', methods=['GET', 'POST'])
def test_email():
    form = EmailForm()
    if request.method == 'POST':
        # send email to [to, cc, bcc] with example subject and content from email_confirmation template
        send_email(TEST_EMAIL, TEST_CC, TEST_BCC, TEST_SUBJECT, 'email_templates/email_confirmation')
        flash('Email sent')
    return render_template('email.html', form=form)
