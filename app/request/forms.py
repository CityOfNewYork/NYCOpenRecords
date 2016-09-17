"""
.. module:: request.forms.

    :synopsis: Defines forms used to create Procurement requests.
"""

from flask_wtf import Form
from wtforms import StringField, SelectField, TextAreaField, SubmitField, DateTimeField
from flask_wtf.file import FileField
from wtforms.validators import DataRequired, Length, Email
from app.constants import categories, agencies, submission_method, states
from datetime import datetime


class PublicUserRequestForm(Form):
    """Form for creating a new FOIL request for public user"""
    # Request Information
    request_category = SelectField('Category', choices=categories)
    request_agency = SelectField('Agency', choices=agencies, validators=[DataRequired('Please select an agency')],
                                 default='')
    request_title = StringField(u'Request Title*', validators=[DataRequired('You must enter a summary of your request'),
                                                               Length(1, 250, 'Your summary must be less than 250'
                                                                              'characters')])
    request_description = TextAreaField(u'Detailed Description*',
                                        validators=[DataRequired('You must enter a description of your request'),
                                                    Length(1, 5001,
                                                           'The detailed description of this request must be less than '
                                                           '5000 characters')])

    # Method Received
    method_received = SelectField(u'Submission Method*', choices=submission_method,
                                  validators=[DataRequired('Please select the submission method')])

    # File Upload
    request_file = FileField()

    request_submit = SubmitField(u'Submit Request')


class AgencyUserRequestForm(Form):
    """Form for creating a new FOIL request for agency user"""
    # Request Information
    request_category = SelectField('Category', choices=categories)
    request_agency = SelectField('Agency (required)', choices=agencies, validators=[DataRequired()])
    request_title = StringField('Request Title (required)', validators=[DataRequired()])
    request_description = TextAreaField('Request Description (required)', validators=[DataRequired()])
    request_date = DateTimeField("Date (required)", format="%Y-%m-%d",
                                 default=datetime.today,
                                 validators=[DataRequired()])

    # Personal Information
    first_name = StringField('First Name (required)', validators=[DataRequired()])
    last_name = StringField('Last Name (required)', validators=[DataRequired()])
    user_title = StringField('Title')
    user_organization = StringField('Organization')

    # Contact Information
    email = StringField('Email', validators=[Email()])
    phone = StringField('Phone', validators=[Length(8, 15)])
    fax = StringField('Fax')
    address = StringField('Address 1')
    address_2 = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=states, default='NY')
    zipcode = StringField('Zipcode', validators=[Length(5, 5)])

    # Method Received
    method_received = SelectField('Format Received (required)', choices=submission_method, validators=[DataRequired()])

    # File Upload
    request_file = FileField('Upload File')

    submit = SubmitField('Submit Request')


class AnonymousRequestForm(Form):
    """Form for creating a new FOIL request for anonymous user"""
    # Request Information
    request_category = SelectField('Category (optional)', choices=categories)
    request_agency = SelectField('Agency (required)', choices=agencies, validators=[DataRequired()])
    request_title = TextAreaField('Request Title (required)', validators=[DataRequired()])
    request_description = TextAreaField('Request Description (required)', validators=[DataRequired()])

    # Personal Information
    first_name = StringField('First Name (required)', validators=[DataRequired()])
    last_name = StringField('Last Name (required)', validators=[DataRequired()])
    user_title = StringField('Title')
    user_organization = StringField('Organization')

    # Contact Information
    email = StringField('Email', validators=[Email()])
    phone = StringField('Phone', validators=[Length(8, 15)])
    fax = StringField('Fax')
    address = StringField('Address 1')
    address_2 = StringField('Address Line 2')
    city = StringField('City')
    state = SelectField('State', choices=states, default='NY')
    zipcode = StringField('Zipcode', validators=[Length(5, 5)])

    # Method Received
    method_received = SelectField('Format Received (required)', choices=submission_method, validators=[DataRequired()])

    # File Upload
    request_file = FileField('Upload File')

    submit = SubmitField('Submit Request')
