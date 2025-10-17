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
    # import urllib.parse
    # import os
    #
    # from azure.identity import DefaultAzureCredential
    #
    # # IMPORTANT! This code is for demonstration purposes only. It's not suitable for use in production.
    # # For example, tokens issued by Microsoft Entra ID have a limited lifetime (24 hours by default).
    # # In production code, you need to implement a token refresh policy.
    #
    # # Read URI parameters from the environment
    # dbhost = os.environ['DBHOST']
    # dbname = os.environ['DBNAME']
    # dbuser = urllib.parse.quote(os.environ['DBUSER'])
    # sslmode = os.environ['SSLMODE']
    #
    # # Use passwordless authentication via DefaultAzureCredential.
    # # IMPORTANT! This code is for demonstration purposes only. DefaultAzureCredential() is invoked on every call.
    # # In practice, it's better to persist the credential across calls and reuse it so you can take advantage of token
    # # caching and minimize round trips to the identity provider. To learn more, see:
    # # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/identity/azure-identity/TOKEN_CACHING.md
    # credential = DefaultAzureCredential()
    #
    # # Call get_token() to get a token from Microsft Entra ID and add it as the password in the URI.
    # # Note the requested scope parameter in the call to get_token, "https://ossrdbms-aad.database.windows.net/.default".
    # password = credential.get_token("https://ossrdbms-aad.database.windows.net/.default").token
    #
    # db_uri = f"postgresql://{dbuser}:{password}@{dbhost}/{dbname}?sslmode={sslmode}"
    # print(db_uri)

    fresh_login = request.args.get('fresh_login', False)
    verify_mfa = request.args.get('verify_mfa', False)
    if current_user.is_authenticated:
        if verify_mfa and current_app.config['USE_MFA']:
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


@main.route('/connect', methods=['GET'])
def connect():
    import urllib.parse
    import os

    from azure.identity import DefaultAzureCredential

    # IMPORTANT! This code is for demonstration purposes only. It's not suitable for use in production.
    # For example, tokens issued by Microsoft Entra ID have a limited lifetime (24 hours by default).
    # In production code, you need to implement a token refresh policy.

    # Read URI parameters from the environment
    dbhost = os.environ['DBHOST']
    dbname = os.environ['DBNAME']
    dbuser = urllib.parse.quote(os.environ['DBUSER'])
    sslmode = 'require'

    # Use passwordless authentication via DefaultAzureCredential.
    # IMPORTANT! This code is for demonstration purposes only. DefaultAzureCredential() is invoked on every call.
    # In practice, it's better to persist the credential across calls and reuse it so you can take advantage of token
    # caching and minimize round trips to the identity provider. To learn more, see:
    # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/identity/azure-identity/TOKEN_CACHING.md
    credential = DefaultAzureCredential()

    # Call get_token() to get a token from Microsft Entra ID and add it as the password in the URI.
    # Note the requested scope parameter in the call to get_token, "https://ossrdbms-aad.database.windows.net/.default".
    password = credential.get_token("https://ossrdbms-aad.database.windows.net/.default").token

    db_uri = f"postgresql://{dbuser}:{password}@{dbhost}/{dbname}?sslmode={sslmode}"

    import psycopg2

    conn_string = db_uri

    conn = psycopg2.connect(conn_string)
    print("Connection established")
    cursor = conn.cursor()

    # Fetch all rows from table
    cursor.execute("SELECT datname FROM pg_database;")
    rows = cursor.fetchall()

    print(rows)

    # Cleanup
    conn.commit()
    cursor.close()
    conn.close()