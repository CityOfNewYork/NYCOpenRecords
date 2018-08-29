# -*- coding: utf-8 -*-
"""ConfigTest Module

This module handles the setup for running tests agains the OpenRecords application.

.. _Flask Tutorial:
   http://flask.pocoo.org/docs/1.0/tutorial/
"""
import sys
import os
import pytest
from app import create_app, db as _db

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))


@pytest.yield_fixture(scope='session')
def app():
    """
    Create a session
    Yields:
        app (Flask): Instance of a Flask application

    """
    _app = create_app(config_name='testing')
    ctx = _app.app_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture(scope='session')
def client(app: Flask):
    """Retrieve an instance of the Flask test_client.

    .. _Flask Test Client:
        http://flask.pocoo.org/docs/1.0/api/#flask.Flask.test_client

    Args:
        app (Flask): Instance of the Flask application

    Returns:
        app.test_client (Flask.test_client): Returns a client used to test the Flask application
    """
    return app.test_client()


@pytest.yield_fixture(scope='session')
def db(app: Flask):
    """
    Create all of the database tables and yield an instance of the database.
    Args:
        app (Flask): Instance of the flask application.

    Yields:
        db (SQLAlchemy): Instance of the SQLAlchemy DB connector
    """
    _db.app = app
    _db.create_all()

    yield _db

    _db.drop_all()


@pytest.fixture(scope='function', autouse=True)
def session(db: SQLAlchemy):
    """Create a database session to be used for the function.

    Args:
        db (SQLAlchemy): Instance of the SQLAlchemy DB connector

    Yields:
        session_ (SQLAlchemy.session): Session object to be used by the function

    """
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session_ = db.create_scoped_session(options=options)

    db.session = session_

    yield session_

    transaction.rollback()
    connection.close()
    session_.remove()
