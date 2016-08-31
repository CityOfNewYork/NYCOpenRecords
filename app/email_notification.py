from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail


def send_async_email(app, msg):
    """
    Sends asynchronous e-mails, allowing the server to avoid delay
        between e-mails.
    :param app: The app to use (passed from send_email)
    :param msg: The message to send (passed from send_email)
    :return: None. Sends message.
    """
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    """
    Sends an e-mail.
    :param to: The recipient
    :param subject: E-mail subject field
    :param template: E-mail template
    :param kwargs: Any additional arguments
    :return: A thread to be used in send_async_email
    """
    app = current_app._get_current_object()
    msg = Message('TimeClock' + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
