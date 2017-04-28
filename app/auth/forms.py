"""

.. module:: auth.forms

    :synopsis: Defines the forms used to manage Authentication requests
"""

from flask_wtf import Form
from wtforms import (
    StringField,
    SelectField,
    PasswordField,
    SubmitField
)

from app.constants import STATES


class ManageUserAccountForm(Form):
    """
    This form manages the OpenRecords specific account fields for a user account:
        Title: The job title for the user (e.g. Reporter); This is optional
        Company: The company for the user (e.g. New York Times); This is optional
        Phone Number: The user's phone number; This is optional
        Fax Number: The user's fax number: This is optional
        Mailing Address: The user's mailing address; Optional;
            Format: Address One, Address Two, City, State, Zip (5 Digits)
    """
    user_title = StringField('Title')
    user_organization = StringField('Organization')
    phone_number = StringField('Phone')
    fax_number = StringField('Fax')
    address_one = StringField('Address Line One')
    address_two = StringField('Address Line Two')
    city = StringField('City')
    state = SelectField('State', choices=STATES, default='NY')
    zipcode = StringField('Zip Code (5 Digits)')

    submit = SubmitField('Update OpenRecords Account')


class LDAPLoginForm(Form):
    email = StringField('Email')
    password = PasswordField('Password')

    login = SubmitField('Login')
