# -*- coding: utf-8 -*-
"""ConfigTest Module

This module handles the setup for running tests agains the OpenRecords application.

.. _Flask Tutorial:
   http://flask.pocoo.org/docs/1.0/tutorial/
"""

import os
import warnings

import pytest
from app import create_app


def weasyprint_cairo_warning():
    warnings.Warn(UserWarning(
        "There are known rendering problems with Cario <= 1.14.0"))


def weasyprint_pango_warning():
    warnings.Warn(UserWarning("@font-face support needs Pango >= 1.38"))


@pytest.fixture
def app():
    app = create_app(
        config_name='testing',
        jobs_enabled=False
    )

    yield app

@pytest.mark.filterwarnings("ignore:weasyprint_pango_warning")
@pytest.mark.filterwarnings("ignore:weasyprint_cairo_warning")
@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
