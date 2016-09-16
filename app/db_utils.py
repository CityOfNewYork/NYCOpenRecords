# TODO: Module Level Comments
"""
    app.db_utils
    ~~~~~~~~~~~~~~~~

"""
from app import db


def create_object(obj):
    db.session.add(obj)
    db.session.commit()


def update_object(**kwargs):
    pass
