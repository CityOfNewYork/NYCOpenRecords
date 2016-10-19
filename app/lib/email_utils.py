#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.lib.email_utils
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
    msg = Message(current_app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=current_app.config['MAIL_SENDER'], recipients=to, cc=cc, bcc=bcc)
    # Renders email template from .txt file commented out and not currently used in development
    # msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    send_async_email.delay(msg)
