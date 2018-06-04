# -*- coding: utf-8 -*-
"""Test Main Module

This module contains the tests for the OpenRecords `/` endpoint.

.. _Flask Tutorial:
   http://flask.pocoo.org/docs/1.0/tutorial/
"""

import pytest

from flask import Flask


def test_home(client: Flask.test_client):
    """ Test the `/` endpoint works properly.

    Args:
        client (Flask.test_client): The test client used to access the endpoint
    """
    response = client.get('/')
    assert b"""<div class="col-sm-12 request-record-button">
            <div class="col-sm-6">
                <a href="/request/view_all">
                    <button class="btn btn-primary btn-lg btn-block request-record-button-size">Check for Similar Requests</button>
                </a>
            </div>
            <div class="col-sm-6">
                <a href="/request/new">
                    <button class="btn btn-primary btn-lg btn-block request-record-button-size">Request a Record</button>
                </a>
            </div>
        </div>""" in response.data
