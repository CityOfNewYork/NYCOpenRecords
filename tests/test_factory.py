# -*- coding: utf-8 -*-
"""Test Factory Module

This module contains the tests for the OpenRecords Application Factory

.. _Flask Tutorial:
   http://flask.pocoo.org/docs/1.0/tutorial/
"""

import pytest
from app import create_app


def test_default_config():
    assert not create_app().testing


def test_testing_config():
    assert create_app(config_name='testing', jobs_enabled=False).testing
