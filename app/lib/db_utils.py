"""
    app.lib.db_utils
    ~~~~~~~~~~~~~~~~
    synopsis: Handles the functions for database control
"""
from app import db, es

from sqlalchemy.orm.attributes import flag_modified
from app.models import (
    Events,
    UserRequests,
    Agencies,
    Requests,
)


def create_object(obj):
    """
    :param obj: Object class being created in database
    :return: Adding and committing object to database
    """
    try:
        db.session.add(obj)
        db.session.commit()
        return str(obj)
    except Exception as e:
        # TODO: email str(e)
        import sys
        print(e)
        print(sys.exc_info())
        db.session.rollback()
        return None


def update_object(data, obj_type, obj_id):
    """

    :param data: a dictionary of attribute-value pairs
    :param obj_type:
    :param obj_id:

    :type obj_type: str

    :return:
    """
    obj = get_obj(obj_type, obj_id)

    if obj:
        for attr, val in data.items():
            setattr(obj, attr, val)
        try:
            if type(value) == dict:
                for key, val in value.items():
                    getattr(obj, attribute)[key] = val
                flag_modified(obj, attribute)
            else:
                setattr(obj, attribute, value)
            db.session.commit()
            obj.es_update()
            return str(obj)
        except Exception as e:
            print(e)
            db.session.rollback()
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
