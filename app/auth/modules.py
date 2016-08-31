"""
.. module:: auth.views.

   :synopsis: Handles all authentication URL endpoints for the
   timeclock application
"""

from werkzeug.security import check_password_hash
from ..models import User
from flask import flash, current_app
from flask_login import current_user
import re


def check_password_requirements(email, old_password, password, password_confirmation):
    """
    Check a password against security requirements.

    :param email: Email of user
    :param old_password: Original password
    :param password: Password that needs to be checked.
    :param password_confirmation: Confirmation of new password
    :return: Boolean (True if valid, False if not)
    """

    user_password = User.query.filter_by(email=email).first().password_hash

    if not check_password_hash(pwhash=user_password, password=old_password):
        current_app.logger.info('%s tried to change their password but failed: entered invalid old password' %
                                current_user.email)
        flash('Your old password did not match', category='warning')
        return False
    if password != password_confirmation:
        current_app.logger.info('%s tried to change their password but failed: passwords did not match' %
                                current_user.email)
        flash('Your passwords do not match', category='warning')
        return False

    # Use a score based system to ensure that users match password requirements
    score = 0
    if re.search('\d+', password):
        # If the password contains a digit, increment score
        score += 1
    if re.search('[a-z]', password) and re.search('[A-Z]', password):
        # If the password contains lowercase and uppercase letters, increment score
        score += 1
    if score < 2:
        current_app.logger.info(current_user.email +
                                'tried to change their password but failed: new password missing uppercase letter '
                                'or number ')
        flash('Your new password must contain eight characters and at least one uppercase letter and one number',
              category='warning')
        return False

    return True
