def create_mailing_address(address_one, city, state, zipcode, address_two=None):
    """
    Creates a JSON object from the parts of a mailing address for a user.

    :param address_one: Line one of the user's address; String
    :param city: City of the user's address; String
    :param state: State of the user's address; String
    :param zipcode: Zip code of the user; 5 Digit integer
    :param address_two: Optional line two of the user's address; String
    :return: JSON Object containing the address
    """
    return {
        'address_one': address_one,  # TODO: constants
        'address_two': address_two,
        'city': city,
        'state': state,
        'zip': zipcode
    }
