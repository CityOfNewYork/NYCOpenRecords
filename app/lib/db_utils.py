"""
    app.lib.db_utils
    ~~~~~~~~~~~~~~~~
    synopsis: Handles the functions for database control
"""
from app import db
from sqlalchemy.orm.attributes import flag_modified
from app.models import Agencies

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
        db.session.rollback()
        return None


def update_object(data, obj_type, obj_id):
    """
    Update a database record.

    :param data: a dictionary of attribute-value pairs
    :param obj_type: sqlalchemy model
    :param obj_id: id of record

    :return: string representation of the updated object
        or None if updating failed
    """
    obj = get_obj(obj_type, obj_id)

    if obj:
        for attr, value in data.items():
            if type(value) == dict:
                # update json values
                for key, val in value.items():
                    getattr(obj, attr)[key] = val
                flag_modified(obj, attr)
            else:
                setattr(obj, attr, value)
        try:
            db.session.commit()
        except Exception as e:
            print("Error:", e)
            db.session.rollback()
        else:
            # update elasticsearch
            if hasattr(obj, 'es_update'):
                obj.es_update()
            return str(obj)
    return None


def get_obj(obj_type, obj_id):
    """

    :param obj_type:
    :param obj_id:
    :return:
    """
    if not obj_id:
        return None
    return obj_type.query.get(obj_id)


def get_agencies_list():
    agencies = sorted([(agencies.ein, agencies.name) for agencies in db.session.query(Agencies).all()],
                      key=lambda x: x[1])
    agencies.insert(0, ('', ''))

    return agencies
