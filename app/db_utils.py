"""
    app.db_utils
    ~~~~~~~~~~~~~~~~
    synopsis: Handles the functions for database control
"""
import json

from app import db

# TODO: Add comment explaining why this is needed
from app.models import Agencies, Users


def create_object(obj):
    """
    :param obj: Object class being created in database
    :return: Adding and committing object to database
    """
    try:
        db.session.add(obj)
        db.session.commit()
        return str(obj)
    except:
        return None


def update_object(attribute, value, obj_type, obj_id):
    """

    :param attribute:
    :param value:
    :param obj_type:
    :param obj_id:
    :return:
    """
    obj = get_obj(obj_type, obj_id)

    if obj:
        try:
            setattr(obj, attribute, value)
            db.session.add(obj)
            db.session.commit(obj)
            return str(obj)
        except:
            return None

    return None


def get_obj(obj_type, obj_id):
    """

    :param obj_type:
    :param obj_id:
    :return:
    """
    if not obj_id:
        return None
    return eval(obj_type).query.get(obj_id)


def get_agencies_list():
    agencies = sorted([(agencies.ein, agencies.name) for agencies in db.session.query(Agencies).all()],
                      key=lambda x: x[1])
    agencies.insert(0, ('', ''))

    return agencies

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
    mailing_address = {
        'address_one': address_one,
        'address_two': address_two,
        'city': city,
        'state': state,
        'zip': zipcode
    }
    mailing_address = json.dumps(mailing_address)

    return mailing_address