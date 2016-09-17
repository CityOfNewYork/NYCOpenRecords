"""
.. module:: request.forms.

    :synopsis: Defines forms used to create Procurement requests.
"""

from datetime import datetime

from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import StringField, SelectField, TextAreaField, SubmitField, DateTimeField

from app.constants import categories, agencies, submission_method, states


class PublicUserRequestForm(Form):
    # Request Information
    request_category = SelectField('Category (optional)', choices=categories)
    request_agency = SelectField('Agency (required)', choices=agencies)
    request_title = StringField('Request Title (required)')
    request_description = TextAreaField('Request Description (required)')
    request_date = DateTimeField("Request Date (required)", format="%Y-%m-%d", default=datetime.today)

    # Personal Information
    first_name = StringField('First Name (required)')
    last_name = StringField('Last Name (required)')
    user_title = StringField('Title')
    user_organization = StringField('Organization')

    # Submit Button
    submit = SubmitField('Submit Request')


class AgencyUserRequestForm(Form):
    """Form for creating a new FOIL request for agency user"""
    # Request Information
    request_category = SelectField('Category', choices=categories)
    request_agency = SelectField('Agency (required)', choices=agencies)
    request_title = StringField('Request Title (required)')
    request_description = TextAreaField('Request Description (required)')
    request_date = DateTimeField("Date (required)", format="%Y-%m-%d", default=datetime.today)

    # Personal Information
    first_name = StringField('First Name (required)')
    last_name = StringField('Last Name (required)')
    user_title = StringField('Title')
    user_organization = StringField('Organization')

    # Contact Information
    email = StringField('Email')
    phone = StringField('Phone')
    fax = StringField('Fax')
    address = StringField('Address 1')
    address_2 = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=states, default='NY')
    zipcode = StringField('Zipcode')

    # Method Received
    method_received = SelectField('Format Received (required)', choices=submission_method)

    # File Upload
    request_file = FileField('Upload File')

    # Submit Button
    submit = SubmitField('Submit Request')


class AnonymousRequestForm(Form):
    """Form for creating a new FOIL request for anonymous user"""
    # Request Information
    request_category = SelectField('Category (optional)', choices=categories)
    request_agency = SelectField('Agency (required)', choices=agencies)
    request_title = TextAreaField('Request Title (required)')
    request_description = TextAreaField('Request Description (required)')

    # Personal Information
    first_name = StringField('First Name (required)')
    last_name = StringField('Last Name (required)')
    user_title = StringField('Title')
    user_organization = StringField('Organization')

    # Contact Information
    email = StringField('Email')
    phone = StringField('Phone')
    fax = StringField('Fax')
    address = StringField('Address 1')
    address_2 = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=states, default='NY')
    zipcode = StringField('Zipcode')

    # Method Received
    method_received = SelectField('Format Received (required)', choices=submission_method)

    # File Upload
    request_file = FileField('Upload File')

    submit = SubmitField('Submit Request')
