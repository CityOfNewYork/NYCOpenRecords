"""
.. module:: request.forms.

    :synopsis: Defines forms used to create Procurement requests.
"""

from datetime import datetime

from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import (
    StringField,
    SelectField,
    TextAreaField,
    SubmitField,
    DateTimeField,
    SelectMultipleField,
)
from sqlalchemy import or_

from app.constants import (
    CATEGORIES,
    STATES,
    submission_methods,
    determination_type,
)
from app.models import Reasons


class PublicUserRequestForm(Form):
    """
    Form for public users to create a new FOIL request.
    For a public user, the required fields are:

    # Request information
    agency: agency selected for the request
    title: name or title of the request
    description: detailed description of the request

    """

    # Request Information
    request_category = SelectField('Category (optional)', choices=CATEGORIES)
    request_agency = SelectField('Agency (required)', choices=None)
    request_title = StringField('Request Title (required)')
    request_description = TextAreaField('Request Description (required)')

    # File Upload
    request_file = FileField('Upload File')

    # Submit Button
    submit = SubmitField('Submit Request')


class AgencyUserRequestForm(Form):
    """
    Form for agency users to create a new FOIL request.
    For an agency user, the required fields are:

    # Request Information
    agency: agency selected for the request
    title: name or title of the request
    description: detailed description of the request
    request_date: date the request was made
    method_received: format the request was received

    # Personal Information
    first_name: first name of the requester
    last_name: last name of the requester

    # Contact Information (at least one form on contact is required)
    email: requester's email address
    phone: requester's phone number
    fax: requester's fax number
    address, city, state, zip: requester's address
    """

    # Request Information
    request_category = SelectField('Category (optional)', choices=CATEGORIES)
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
    address_two = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=STATES, default='NY')
    zipcode = StringField('Zip')

    # Method Received
    method_received = SelectField('Format Received (required)',
                                  choices=submission_methods.AS_CHOICES)

    # File Upload
    request_file = FileField('Upload File')

    # Submit Button
    submit = SubmitField('Submit Request')


class AnonymousRequestForm(Form):
    """
    Form for anonymous users to create a new FOIL request.
    For a anonymous user, the required fields are:

    # Request Information
    agency: agency selected for the request
    title: name or title of the request
    description: detailed description of the request

    # Personal Information
    first_name: first name of the requester
    last_name: last name of the requester

    # Contact Information (at least one form on contact is required)
    email: requester's email address
    phone: requester's phone number
    fax: requester's fax number
    address, city, state, zip: requester's address
    """
    # Request Information
    request_category = SelectField('Category (optional)', choices=CATEGORIES)
    request_agency = SelectField('Agency (required)', choices=None)
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
    address_two = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=STATES, default='NY')
    zipcode = StringField('Zip')

    # File Upload
    request_file = FileField('Upload File')

    submit = SubmitField('Submit Request')


class EditRequesterForm(Form):
    email = StringField('Email')
    phone = StringField('Phone Number')
    fax = StringField('Fax Number')
    address_one = StringField('Address Line 1')
    address_two = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=STATES)
    zipcode = StringField('Zip Code')
    title = StringField('Title')
    organization = StringField('Organization')

    def __init__(self, requester):
        """
        :type requester: app.models.Users
        """
        super(EditRequesterForm, self).__init__()
        self.email.data = requester.email or ""
        self.phone.data = requester.phone_number or ""
        self.fax.data = requester.fax_number or ""
        self.title.data = requester.title or ""
        self.organization.data = requester.organization or ""
        if requester.mailing_address is not None:
            self.address_one.data = requester.mailing_address.get("address_one") or ""
            self.address_two.data = requester.mailing_address.get("address_two") or ""
            self.city.data = requester.mailing_address.get("city") or ""
            self.state.data = requester.mailing_address.get("state") or ""
            self.zipcode.data = requester.mailing_address.get("zip") or ""


class DenyRequestForm(Form):
    reasons = SelectMultipleField('Reasons for Denial (Choose 1 or more)')

    def __init__(self, agency_ein):
        super(DenyRequestForm, self).__init__()
        self.reasons.choices = [
            (reason.id, reason.content)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.DENIAL,
                or_(
                    Reasons.agency_ein == agency_ein,
                    Reasons.agency_ein == None
                )
            )]
