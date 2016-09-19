"""
    app.db_utils
    ~~~~~~~~~~~~~~~~
    synopsis: Handles the functions for database control
"""
from app import db


def create_object(obj):
    """
    :param obj: Object class being created in database
    :return: Adding and committing object to database
    """
    db.session.add(obj)
    db.session.commit()


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