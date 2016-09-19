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


def update_object(**kwargs):
    pass
