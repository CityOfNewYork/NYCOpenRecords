"""
 .. module: utils

"""


def mapping(**named_values):
    return type('Map'
                'ping', (), named_values)
