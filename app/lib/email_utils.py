#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.email_utils
    ~~~~~~~~~~~~~~~~

    Implements e-mail notifications for OpenRecords. Flask-mail is a dependency, and the following environment variables
    need to be set in order for this to work: (Currently using Fake SMTP for testing)
        MAIL_SERVER: 'localhost'
        MAIL_PORT: 2500
        MAIL_USE_TLS: FALSE
        MAIL_USERNAME: os.environ.get('MAIL_USERNAME')
        MAIL_PASSWORD: os.environ.get('MAIL_PASSWORD')
        DEFAULT_MAIL_SENDER: 'Records Admin <openrecords@records.nyc.gov>'

"""

from flask import current_app, render_template
from flask_mail import Message

from app import mail, celery
from app.lib.db_utils import create_object
from app.models import Emails


@celery.task
def send_async_email(msg):
    mail.send(msg)


def send_email(subject, template, to=list(), cc=list(), bcc=list(), **kwargs):
    """
    Function that sends asynchronous emails for the application.
    Takes in arguments from the frontend.

    :param to: Person(s) email is being sent to
    :param cc: Person(s) being CC'ed on the email
    :param bcc: Person(s) being BCC'ed on the email
    :param subject: Subject of the email
    :param template: HTML and TXT template of the email content
    :param kwargs: Additional arguments the function may take in (ie: Message content)
    :return: Sends email asynchronously
    """
    assert to or cc or bcc
    app = current_app._get_current_object()
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=to, cc=cc, bcc=bcc)
    # Renders email template from .txt file commented out and not currently used in development
    # msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    send_async_email.delay(msg)


def store_email(subject, email_content, to=None, cc=None, bcc=None):
    """
    Creates and stores an email object for the specified request.

    :param subject: subject of the email to be created and stored as a email object
    :param email_content: email body content of the email to be created and stored as a email object
    :param to: list of person(s) email is being sent to
    :param cc: list of person(s) email is being cc'ed to
    :param bcc: list of person(s) email is being bcc'ed
    :return: Stores the email metadata into the Emails table.
             Provides parameters for the process_response function to create and store responses and events object.
    """
    to = ','.join([email.replace('{', '').replace('}', '') for email in to]) if to else None
    cc = ','.join([email.replace('{', '').replace('}', '') for email in cc]) if cc else None
    bcc = ','.join([email.replace('{', '').replace('}', '') for email in bcc]) if bcc else None
    email = Emails(to=to, cc=cc, bcc=bcc, subject=subject, email_content=email_content)
    create_object(obj=email)
