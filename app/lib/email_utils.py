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

from app import mail, celery, sentry
from app.models import Requests


@celery.task(serializer='pickle')
def send_async_email(msg):
    try:
        mail.send(msg)
    except Exception as e:
        sentry.captureException()
        current_app.logger.exception("Failed to Send Email {} : {}".format(msg, e))


def send_contact_email(subject, recipients, body, sender):
    msg = Message(subject, recipients, body, sender=sender)
    send_async_email.delay(msg)


def send_email(subject, to=list(), cc=list(), bcc=list(), reply_to='', template=None, email_content=None, **kwargs):
    """Function that sends asynchronous emails for the application.
    Takes in arguments from the frontend.

    Args:
        to: Person(s) email is being sent to
        cc: Person(s) being CC'ed on the email
        bcc: Person(s) being BCC'ed on the email
        reply_to: reply-to address
        subject: Subject of the email
        template: HTML and TXT template of the email content
        email_content: string of HTML email content that can be used as a message template
        kwargs: Additional arguments the function may take in (ie: Message content)
    """
    assert to or cc or bcc
    msg = Message(current_app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=current_app.config['MAIL_SENDER'],
                  recipients=to,
                  cc=cc,
                  bcc=bcc,
                  reply_to=reply_to)
    # Renders email template from .txt file commented out and not currently used in development
    # msg.body = render_template(template + '.txt', **kwargs)
    if email_content:
        msg.html = email_content
    else:
        msg.html = render_template(template + '.html', **kwargs)

    attachment = kwargs.get('attachment', None)
    if attachment:
        filename = kwargs.get('filename')
        mimetype = kwargs.get('mimetype', 'application/pdf')
        msg.attach(filename, mimetype, attachment)
    send_async_email.delay(msg)


def get_agency_emails(request_id, admins_only=False):
    """
    Gets a list of the agency emails (assigned users and default email)

    :param request_id: FOIL request ID to query UserRequests
    :param admins_only: return list of agency admin emails only
    :return: list of agency emails or ['agency@email.com'] (for testing)
    """
    request = Requests.query.filter_by(id=request_id).one()

    if admins_only:
        return list(set(user.notification_email if user.notification_email is not None else user.email for user in
                        request.agency.administrators))

    return list(set([user.notification_email if user.notification_email is not None else user.email for user in
                     request.agency_users] + [request.agency.default_email]))
