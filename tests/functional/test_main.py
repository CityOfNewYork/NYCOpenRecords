# -*- coding: utf-8 -*-
"""Test Main Module

This module contains the tests for the OpenRecords `/` endpoint.
"""

import pytest
import utils

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import Emails


def test_index(client: Flask.test_client):
    """ Test the `/` endpoint works properly.

    Args:
        client (Flask.test_client): The test client used to access the endpoint
    """
    response = client.get("/")
    print(response.data)
    assert b"""                    <button class="btn btn-primary btn-lg btn-block request-record-button-size">Check for Similar
                        Requests
                    </button>""" in response.data
    assert b"""<button class="btn btn-primary btn-lg btn-block request-record-button-size">Request a Record
                    </button>""" in response.data


def test_status(client: Flask.test_client):
    """Test the `/index.html` and `/status` status endpoint always returns 200 on GET

    Args:
        client (Flask.test_client): The test client used to access the endpoint
    """
    # Test `/index.html`
    response = client.get("/index.html")
    assert response.status_code == 200

    response = client.post("/index.html")
    assert response.status_code == 405

    # Test `/status`
    response = client.get("/status")
    assert response.status_code == 200
    response = client.post("/status")
    assert response.status_code == 405


def test_get_contact(
        client: Flask.test_client
):
    """Test the technical support endpoint / form for OpenRecords

    Args:
        client (Flask.test_client): Test client used to access the technical-support page
    """

    # Test `/technical-support`
    response = client.get("/contact")
    assert response.status_code == 200
    assert b'<h1 class="text-center">Technical Support</h1>' in response.data
    assert b"Use this form only for technical support." in response.data


@pytest.mark.parametrize(
    ("name", "email", "subject", "message", "app_response", "num_db_entries"),
    (
            (
                    "John Doris",
                    "john.doris@records.nyc.gov",
                    "Test Subject",
                    "Test Message",
                    b"Your message has been sent. We will get back to you.",
                    1
            ),
            ("", "john.doris@records.nyc.gov", "Test Subject",
             "Test Message", b"Cannot send email.", 0),
            ("John Doris", "", "Test Subject", "Test Message", b"Cannot send email.", 0),
            ("John Doris", "john.doris@records.nyc.gov",
             "", "Test Message", b"Cannot send email.", 0),
            ("John Doris", "john.doris@records.nyc.gov",
             "Test Subject", "", b"Cannot send email", 0),
            ("", "", "", "", b"Cannot send email.", 0),
    ),
)
def test_post_contact(
        db: SQLAlchemy, client: Flask.test_client, name: str, email: str, subject: str, message: bytes,
        app_response: str, num_db_entries: int
):
    """Test the technical support form for OpenRecords

    Args:
        db (SQLAlchemy): DB instance setup for testing.
        client (Flask.test_client): Test client used to access the technical-support page
        name (str): Name of the person submitting the form (required)
        email (str): Email of the person submitting the form (required)
        subject (str): Subject of the message being sent out
        message (str): Message being sent out
        app_response (str): Message displayed after post
        num_db_entries (int): Number of database entries that should exist after post
    """
    data = {"name": name, "email": email, "subject": subject,
            "message": message, "app_response": app_response}
    response = client.post("/contact", data=data)
    assert response.status_code == 200
    assert app_response in response.data
    assert len(Emails.query.all()) == num_db_entries

    utils.clear_data(db)


def test_get_technical_support(
        client: Flask.test_client
):
    """Test the technical support endpoint / form for OpenRecords

    Args:
        client (Flask.test_client): Test client used to access the technical-support page
    """

    # Test `/technical-support`
    response = client.get("/technical-support")
    assert response.status_code == 200
    assert b'<h1 class="text-center">Technical Support</h1>' in response.data
    assert b"Use this form only for technical support." in response.data


@pytest.mark.parametrize(
    ("name", "email", "subject", "message", "app_response", "num_db_entries"),
    (
            (
                    "John Doris",
                    "john.doris@records.nyc.gov",
                    "Test Subject",
                    "Test Message",
                    b"Your message has been sent. We will get back to you.",
                    1
            ),
            ("", "john.doris@records.nyc.gov", "Test Subject",
             "Test Message", b"Cannot send email.", 0),
            ("John Doris", "", "Test Subject", "Test Message", b"Cannot send email.", 0),
            ("John Doris", "john.doris@records.nyc.gov",
             "", "Test Message", b"Cannot send email.", 0),
            ("John Doris", "john.doris@records.nyc.gov",
             "Test Subject", "", b"Cannot send email", 0),
            ("", "", "", "", b"Cannot send email.", 0),
    ),
)
def test_post_technical_support(
        db: SQLAlchemy, client: Flask.test_client, name: str, email: str, subject: str, message: bytes,
        app_response: str, num_db_entries: int
):
    """Test the technical support form for OpenRecords

    Args:
        db (SQLAlchemy): DB instance setup for testing.
        client (Flask.test_client): Test client used to access the technical-support page
        name (str): Name of the person submitting the form (required)
        email (str): Email of the person submitting the form (required)
        subject (str): Subject of the message being sent out
        message (str): Message being sent out
        app_response (str): Message displayed after post
        num_db_entries (int): Number of database entries that should exist after post
    """
    data = {"name": name, "email": email, "subject": subject,
            "message": message, "app_response": app_response}
    response = client.post("/contact", data=data)
    assert response.status_code == 200
    assert app_response in response.data
    assert len(Emails.query.all()) == num_db_entries

    utils.clear_data(db)


def test_faq(
        client: Flask.test_client
):
    """Test the FAQ page for OpenRecords

    Args:
        client (Flask.test_client: Test client used toa ccess the FAQ page
    """
    response = client.get('/faq')
    assert response.status_code == 200
    assert b'<h1 class="text-center" id="faq-header" tabindex="0">Frequently Asked Questions</h1>' in response.data


def test_about(
        client: Flask.test_client
):
    """Test the FAQ page for OpenRecords

    Args:
        client (Flask.test_client: Test client used toa ccess the FAQ page
    """
    response = client.get('/about')
    assert response.status_code == 200
    assert b'''<h1 id="about" class="text-center">
                About OpenRECORDS
            </h1>''' in response.data
