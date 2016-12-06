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
from app.lib.email_utils import send_email
from flask_wtf import Form
from wtforms import SubmitField, StringField

from app.models import Users
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('home.html')


# TESTING PURPOSES
class EmailForm(Form):
    to = StringField('To')
    cc = StringField('CC')
    bcc = StringField('BCC')
    subject = StringField('Subject')
    submit = SubmitField('Send Email')


# Used for testing email functionality
@main.route('/email', methods=['GET', 'POST'])
def test_email():
    form = EmailForm()
    if request.method == 'POST':
        # send email to [to, cc, bcc] with example subject and content from email_confirmation template
        to = 'test@email.com' if 'to' not in request.form else form.to.data
        cc = 'test_cc@email.com' if 'cc' not in request.form else form.cc.data
        bcc = 'test_bcc@email.com' if 'bcc' not in request.form else form.bcc.data
        subject = 'Test Subject' if 'subject' not in request.form else form.subject.data
        send_email(to, cc, bcc, subject, 'email_templates/email_confirmation')
        flash('Email sent')
    return render_template('email.html', form=form)


@main.route('/index.html', methods=['GET'])
def status():
    return 200
