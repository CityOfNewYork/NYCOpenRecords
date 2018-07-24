# -*- coding: utf-8 -*-
"""helper.utils Module

This module contains helper functions for running tests.

"""
import pytest
from flask_sqlalchemy import SQLAlchemy

from app.models import Requests

def clear_data(db: SQLAlchemy):
    """Clear the data in the database after a test.
    Args:
        db (SQLAlchemy): Instance of the database.

    Returns:

    """
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        # print('Clear table %s' % table)
        db.session.execute(table.delete())
    db.session.commit()


def create_request():
    """

    Returns:

    """
    pass