"""
 .. module: utils

"""
from flask_login import current_user

def mapping(**named_values):
    return type('Mapping', (), named_values)


class InvalidUserException(Exception):

    def __init__(self, user):
        """
        :param user: the current_user as define in flask_login
        """
        super(InvalidUserException, self).__init__(
            "Invalid user: {}".format(user))
