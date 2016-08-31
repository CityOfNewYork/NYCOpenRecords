from openrecords import app
from openrecords.models import User


def authenticate_login(email, password):
    """
    Authenticate the user logging in

    :param email: Users email address
    :type email: string
    :param password: Users password
    :type password: string
    :return: The user object, if the user is authenticated, otherwise None
    :rtype: User object
    """
    if app.config['USE_SAML'] == 'True':
        app.logger.info('Using SAML to log in')
    else:
        user = User.query.filter_by(email=email.lower()).first()
        if user and (user.is_staff or user.is_admin()):
            if user.check_password(password):
                return user
        return None
