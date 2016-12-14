"""
.. module:: main.views.

   :synopsis: Handles all core URL endpoints for the timeclock application
"""

from flask import (
    render_template,
    flash,
    request,
    redirect,
    url_for
)
from flask_login import login_user, current_user, logout_user
from flask_wtf import Form
from wtforms import SubmitField, StringField

from app.constants.user_type_auth import (
    AGENCY_USER,
    PUBLIC_USER_TYPES
)
from app.lib.email_utils import send_email
from app.models import Users
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('main/home.html')


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


@main.route('/about', methods=['GET'])
def about():
    return render_template('main/about.html')

@main.route('/login')
@main.route('/login/<guid>', methods=['GET'])
def login(guid=None):
    if guid:
        user = Users.query.filter_by(guid=guid).one()
        login_user(user, force=True)
        flash('Logged in user: {}'.format(user.auth_user_type))
        return redirect(url_for('main.index'))
    types = [type for type in PUBLIC_USER_TYPES]
    types.append(AGENCY_USER)
    users = []
    for type_ in types:
        user = Users.query.filter_by(auth_user_type=type_).first()
        users.append(user)

    return render_template('main/test/user_list.html', users=users, current_user=current_user)

#
# @main.route('/login-user/<guid>', methods=['GET'])
# def test_specific_user(guid=None):
#     user = Users.query.filter_by(guid=guid).first()
#     login_user(user, force=True)
#     return redirect(url_for('main.index'))

@main.route('/logout-user/<guid>', methods=['GET'])
def logout(guid):
    if not guid:
        return(redirect(url_for('main.login')))
    user = Users.query.filter_by(guid=guid).one()
    logout_user()
    flash('Logged out user: {}'.format(user.auth_user_type))
    return redirect(url_for('main.index'))
