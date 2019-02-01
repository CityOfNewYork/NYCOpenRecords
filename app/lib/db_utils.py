"""
    app.lib.db_utils
    ~~~~~~~~~~~~~~~~
    synopsis: Handles the functions for database control
"""
from flask import current_app
from app import db, sentry
from app.models import Agencies, Requests
from app.constants import HIDDEN_AGENCIES
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified


def create_object(obj):
    """
    Add a database record and its elasticsearch counterpart.

    If 'obj' is a Requests object, nothing will be added to
    the es index since a UserRequests record is created after
    its associated request and the es doc requires a
    requester id. 'es_create' is called explicitly for a
    Requests object in app.request.utils.

    :param obj: object (instance of sqlalchemy model) to create

    :return: string representation of created object
        or None if creation failed
    """
    try:
        db.session.add(obj)
        db.session.commit()
    except SQLAlchemyError:
        sentry.captureException()
        db.session.rollback()
        current_app.logger.exception("Failed to CREATE {}".format(obj))
        return None
    else:
        # create elasticsearch doc
        if (
                not isinstance(obj, Requests)
                and hasattr(obj, 'es_create')
                and current_app.config['ELASTICSEARCH_ENABLED']
        ):
            obj.es_create()
        return str(obj)


def update_object(data, obj_type, obj_id, es_update=True):
    """
    Update a database record and its elasticsearch counterpart.

    :param data: a dictionary of attribute-value pairs
    :param obj_type: sqlalchemy model
    :param obj_id: id of record
    :param es_update: update the elasticsearch index

    :return: was the record updated successfully?
    """
    obj = get_object(obj_type, obj_id)

    if obj:
        for attr, value in data.items():
            if isinstance(value, dict):
                # update json values
                attr_json = getattr(obj, attr) or {}
                for key, val in value.items():
                    attr_json[key] = val
                setattr(obj, attr, attr_json)
                flag_modified(obj, attr)
            else:
                setattr(obj, attr, value)
        try:
            db.session.commit()
        except SQLAlchemyError:
            sentry.captureException()
            db.session.rollback()
            current_app.logger.exception("Failed to UPDATE {}".format(obj))
        else:
            # update elasticsearch
            if hasattr(obj, 'es_update') and current_app.config['ELASTICSEARCH_ENABLED'] and es_update:
                obj.es_update()
            return True
    return False


def delete_object(obj):
    """
    Delete a database record.

    :param obj: object (instance of sqlalchemy model) to delete
    :return: was the record deleted successfully?
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        return True
    except SQLAlchemyError:
        sentry.captureException()
        db.session.rollback()
        current_app.logger.exception("Failed to DELETE {}".format(obj))
        return False


def bulk_delete(query):
    """
    Delete multiple database records via a bulk delete query.

    http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.delete

    :param query: Query object
    :return: the number of records deleted
    """
    try:
        num_deleted = query.delete()
        db.session.commit()
        return num_deleted
    except SQLAlchemyError:
        sentry.captureException()
        db.session.rollback()
        current_app.logger.exception("Failed to BULK DELETE {}".format(query))
        return 0


def get_object(obj_type, obj_id):
    """
    Safely retrieve a database record by its id
    and its sqlalchemy object type.
    """
    if not obj_id:
        return None
    try:
        return obj_type.query.get(obj_id)
    except SQLAlchemyError:
        sentry.captureException()
        db.session.rollback()
        current_app.logger.exception('Error searching "{}" table for id {}'.format(
            obj_type.__tablename__, obj_id))
        return None


def get_agency_choices():
    choices = sorted([(agencies.ein, agencies.name)
                      for agencies in db.session.query(Agencies).all() if agencies.ein not in HIDDEN_AGENCIES],
                     key=lambda x: x[1])
    return choices
