"""
 .. module: lib

"""


def mapping(**named_values):
    return type('Mapping', (), named_values)
