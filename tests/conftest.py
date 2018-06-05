# -*- coding: utf-8 -*-
"""ConfigTest Module

This module handles the setup for running tests agains the OpenRecords application.

.. _Flask Tutorial:
   http://flask.pocoo.org/docs/1.0/tutorial/
"""
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as AlembicConfig

from app import create_app
from config import config as base_config


def pytest_configure(config):
    sys._called_from_test = True


def pytest_unconfigure(config):
    del sys._called_from_test


@pytest.fixture(scope='session')
def flask_app(request):
    app = create_app('testing')
    print('\n----- CREATE FLASK APPLICATION\n')

    context = app.app_context()
    context.push()
    yield app
    print('\n----- CREATE FLASK APPLICATION CONTEXT\n')

    context.pop()
    print('\n----- RELEASE FLASK APPLICATION CONTEXT\n')


@pytest.fixture(scope='session')
def client(request, flask_app):
    print('\n----- CREATE FLASK TEST CLIENT\n')
    return flask_app.test_client()


@pytest.fixture(scope='session')
def db(request):
    config = base_config['testing']
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=True)
    session_factory = sessionmaker(bind=engine)
    print('\n----- CREATE TEST DB CONNECTION POOL\n')

    _db = {
        'engine': engine,
        'session_factory': session_factory,
    }
    _db.create_all()
    print('\n----- RUN ALEMBIC MIGRATION\n')
    yield _db
    print('\n----- CREATE TEST DB INSTANCE POOL\n')

    engine.dispose()
    print('\n----- RELEASE TEST DB CONNECTION POOL\n')


@pytest.fixture(scope='function')
def session(request, db):
    session = db['session_factory']()
    yield session
    print('\n----- CREATE DB SESSION\n')

    session.rollback()
    session.close()
    print('\n----- ROLLBACK DB SESSION\n')
