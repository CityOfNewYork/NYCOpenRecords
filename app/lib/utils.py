"""
 .. module: utils

"""


def mapping(**named_values):
    return type('Mapping', (), named_values)


class InvalidUserException(Exception):

    def __init__(self, user):
        super(InvalidUserException, self).__init__(
            "Invalid user: {}".format(user))
