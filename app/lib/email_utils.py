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
from app.models import Users, UserRequests, Requests
from app.constants.user_type_request import AGENCY
from app.constants.user_type_auth import AGENCY_USER


@celery.task
def send_async_email(msg):
    mail.send(msg)


def send_email(subject, to=list(), cc=list(), bcc=list(), template=None, email_content=None, **kwargs):
    """
    Function that sends asynchronous emails for the application.
    Takes in arguments from the frontend.

    :param to: Person(s) email is being sent to
    :param cc: Person(s) being CC'ed on the email
    :param bcc: Person(s) being BCC'ed on the email
    :param subject: Subject of the email
    :param template: HTML and TXT template of the email content
    :param email_content: string of HTML email content that can be used as a message template
    :param kwargs: Additional arguments the function may take in (ie: Message content)
    """
    assert to or cc or bcc
    msg = Message(current_app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=current_app.config['MAIL_SENDER'], recipients=to, cc=cc, bcc=bcc)
    # Renders email template from .txt file commented out and not currently used in development
    # msg.body = render_template(template + '.txt', **kwargs)
    if email_content:
        msg.html = email_content
    else:
        msg.html = render_template(template + '.html', **kwargs)
    send_async_email.delay(msg)


def get_agencies_emails(request_id):
    """
    Gets a list of the agencies emails by querying UserRequests by request_id and request_user_type

    :param request_id: FOIL request ID to query UserRequests
    :return: list of agency emails or ['agency@email.com'] (for testing)
    """
    # Get list of agency users on the request
    agency_user_guids = UserRequests.query.with_entities(UserRequests.user_guid).filter_by(request_id=request_id,
                                                                                           request_user_type=AGENCY).all()
    # Query for the agency email information
    agency_emails = []  # FIXME: Can this be empty?
    for user_guid in agency_user_guids:
        agency_user_email = Users.query.filter_by(guid=user_guid, auth_user_type=AGENCY_USER).first().email
        agency_emails.append(agency_user_email)
    # get the agency_ein's default email and adds it to the bcc list
    agency_default_email = Requests.query.filter_by(id=request_id).first().agency.default_email
    agency_emails.append(agency_default_email)
    return agency_emails or ['agency@email.com']
