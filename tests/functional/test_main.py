# -*- coding: utf-8 -*-
"""Test Main Module

This module contains the tests for the OpenRecords `/` endpoint.

.. _Flask Tutorial:
   http://flask.pocoo.org/docs/1.0/tutorial/
"""

import pytest

from flask import Flask


def test_index(client: Flask.test_client):
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


def test_status(client: Flask.test_client):
    """Test the `/index.html` and `/status` status endpoint always returns 200 on GET

    Args:
        client (Flask.test_client): The test client used to access the endpoint
    """
    # Test `/index.html`
    response = client.get('/index.html')
    assert response.status_code == 200

    response = client.post('/index.html')
    assert response.status_code == 405

    # Test `/status`
    response = client.get('/status')
    assert response.status_code == 200
    response = client.post('/status')
    assert response.status_code == 405


@pytest.mark.parametrize(
    ('name', 'email', 'subject', 'message', 'error'),
    (('John Doris', 'john.doris@records.nyc.gov', 'Test Subject', 'Test Message',
      b'Your message has been sent. We will get back to you.'),
     ('', 'john.doris@records.nyc.gov', 'Test Subject', 'Test Message', b'Cannot send email.'),
     ('John Doris', '', 'Test Subject', 'Test Message', b'Cannot send email.'),
     ('John Doris', 'john.doris@records.nyc.gov', '', 'Test Message', b'Cannot send email.'),
     ('John Doris', 'john.doris@records.nyc.gov', 'Test Subject', '',
      b'Cannot send email'),
     ('', '', '', '', b'Cannot send email.')
     )
)
def test_technical_support_page(client: Flask.test_client, db, name: str, email: str, subject: str, message: bytes,
                                error: str):
    """Test the technical support endpoint / form for OpenRecords

    Args:
        client (Flask.test_client): Test client used to access the technical-support page
        name (str): Name of the person submitting the form (required)
        email (str): Email of the person submitting the form (required)
        subject (str): Subject of the message being sent out
        message (str): Message being sent out
        error (str): Message displayed after post
    """
    data = {
        'name': name,
        'email': email,
        'subject': subject,
        'message': message,
        'error': error
    }

    # Test `/contact`/
    response = client.get('/contact')
    assert response.status_code == 200
    assert b'<h2 class="text-center">Technical Support</h2>' in response.data
    assert b'Use this form only for technical support.' in response.data
    pytest.set_trace()
    response = client.post('/contact', data=data)
    assert response.status_code == 200
    assert error in response.data


    # # Test `/technical-support`
    # response = client.get('/technical-support')
    # assert response.status_code == 200
    # assert b'<h2 class="text-center">Technical Support</h2>' in response.data
    # assert b'<p align="center">Use this form only for technical support. Agency contact for other questions and information is available within the actual request.</p>' in response.data
    # response = client.post('/technical-support', data=data)
    # assert response.status_code == 200
    # assert message in response.data
