"""
    app.lib.db_utils
    ~~~~~~~~~~~~~~~~
    synopsis: Handles the functions for database control
"""
import sys
from flask import current_app
from app import db
from app.models import Agencies, Requests
from sqlalchemy.orm.attributes import flag_modified


def create_object(obj):
    """
    Add a database record and its elasticsearch counterpart.

    If 'obj' is a Requests object, nothing will be added to
    the es index since a UserRequests record is created after
    its associated request and the es doc requires a
    requester id. 'es_create' is called explicitly for a
    Requests object in app.request.utils.

    :param obj: Object class being created in database

    :return: Adding and committing object to database
    """
    try:
        db.session.add(obj)
        db.session.commit()
    except Exception as e:
        print("Failed to CREATE {} : {}".format(obj, e))
        print(sys.exc_info())
        db.session.rollback()
        return None
    else:
        # create elasticsearch doc
        if not isinstance(obj, Requests) and hasattr(obj, 'es_create') and current_app.config['ELASTICSEARCH_ENABLED']:
            obj.es_create()
        return str(obj)


def update_object(data, obj_type, obj_id):
    """
    Update a database record and its elasticsearch counterpart.

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
            print("Failed to UPDATE {} : {}".format(obj, e))
            print(sys.exc_info())
            db.session.rollback()
        else:
            # update elasticsearch
            if hasattr(obj, 'es_update') and current_app.config['ELASTICSEARCH_ENABLED']:
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
    agencies = sorted([(agencies.ein, agencies.name)
                       for agencies in db.session.query(Agencies).all()],
                      key=lambda x: x[1])
    agencies.insert(0, ('', ''))

    return agencies
