#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.email_utils
    ~~~~~~~~~~~~~~~~

    Implements e-mail notifications for OpenRecords. Flask-mail is a dependency, and the following environment variables
    need to be set in order for this to work:
        MAIL_SERVER:
        MAIL_PORT:
        MAIL_USE_TLS:
        MAIL_USERNAME:
        MAIL_PASSWORD:
        DEFAULT_MAIL_SENDER:

"""

from threading import Thread
from flask.ext.mail import Message
from app import app, mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    """

    :param subject:
    :param sender:
    :param recipients:
    :param text_body:
    :param html_body:
    :return:
    """
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    msg.html = html_body
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
