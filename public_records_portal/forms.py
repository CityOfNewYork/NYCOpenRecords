__author__ = 'jcastillo'
from flask.ext.wtf import Form
from wtforms import StringField, SelectField, TextAreaField, DateField, BooleanField, PasswordField, SubmitField, FileField
from wtforms_components import PhoneNumberField, Email
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from flask.ext.login import current_user
from flask import Flask
from flask_recaptcha import ReCaptcha
from public_records_portal import db, models
app = Flask(__name__)

agency = db.session.query(models.Agency).all()
agencies = [('', '')]
for a in agency:
    agencies.append((a.name, a.name))
agencies.append(('Unknown', 'I Don\'t Know'))

categories = [
    ('',''),
    ('Business', 'Business'),
    ('Civic Services', 'Civic Services'),
    ('Culture & Recreation', 'Culture & Recreation'),
    ('Education', 'Education'),
    ('Environment', 'Environment'),
    ('Health', 'Health'),
    ('Housing & Development', 'Housing & Development'),
    ('Public Safety', 'Public Safety'),
    ('Social Services', 'Social Services'),
    ('Transportation', 'Transportation')
]

formats = [
    ('', ''),
    ('Fax', 'Fax'),
    ('Phone', 'Phone'),
    ('Email', 'Email'),
    ('Mail', 'Mail'),
    ('In-Person', 'In-Person'),
    ('Text Message', 'Text Message'),
    ('311', '311')
]

states = [
    ('', ''),
    ('AL', 'Alabama'),
    ('AK', 'Alaska'),
    ('AZ', 'Arizona'),
    ('AR', 'Arkansas'),
    ('CA', 'California'),
    ('CO', 'Colorado'),
    ('CT', 'Connecticut'),
    ('DE', 'Delaware'),
    ('DC', 'District Of Columbia'),
    ('FL', 'Florida'),
    ('GA', 'Georgia'),
    ('HI', 'Hawaii'),
    ('ID', 'Idaho'),
    ('IL', 'Illinois'),
    ('IN', 'Indiana'),
    ('IA', 'Iowa'),
    ('KS', 'Kansas'),
    ('KY', 'Kentucky'),
    ('LA', 'Louisiana'),
    ('ME', 'Maine'),
    ('MD', 'Maryland'),
    ('MA', 'Massachusetts'),
    ('MI', 'Michigan'),
    ('MN', 'Minnesota'),
    ('MS', 'Mississippi'),
    ('MO', 'Missouri'),
    ('MT', 'Montana'),
    ('NE', 'Nebraska'),
    ('NV', 'Nevada'),
    ('NH', 'New Hampshire'),
    ('NJ', 'New Jersey'),
    ('NM', 'New Mexico'),
    ('NY', 'New York'),
    ('NC', 'North Carolina'),
    ('ND', 'North Dakota'),
    ('OH', 'Ohio'),
    ('OK', 'Oklahoma'),
    ('OR', 'Oregon'),
    ('PA', 'Pennsylvania'),
    ('RI', 'Rhode Island'),
    ('SC', 'South Carolina'),
    ('SD', 'South Dakota'),
    ('TN', 'Tennessee'),
    ('TX', 'Texas'),
    ('UT', 'Utah'),
    ('VT', 'Vermont'),
    ('VA', 'Virginia'),
    ('WA', 'Washington'),
    ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'),
    ('WY', 'Wyoming')
]

privacy_options = [
    (1, 'Yes'),
    (2, 'No')
]

class OfflineRequestForm(Form):
    # Fields
    request_category = SelectField(u'Category*', choices=categories, validators=[DataRequired('The request category is required')])

    request_text = TextAreaField(u'Request Description*', validators=[
        DataRequired('The request description is required'),
        Length(1, 5000, 'Your request must be less than 5000 characters')])
    request_format = SelectField(u'Format Received*', choices=formats,
                                 validators=[DataRequired('You must enter a request format')],
                                 default='')
    request_date = DateField(u'Request Date*', format='%m/%d/%Y',
                             validators=[DataRequired(
                                 'You must enter the request date')])
    request_department = SelectField(u'Request Department*', choices=agencies,
                                     validators=[DataRequired('Please choose a department')], default='')
    request_first_name = StringField(
        u'First Name*', validators=[DataRequired('Please enter the requestor\'s first name')])
    request_last_name = StringField(
        u'Last Name*', validators=[DataRequired('Please enter the requestor\'s last name')])
    request_privacy = SelectField(u'Privacy Options', choices=privacy_options, validators=[DataRequired('You must select a privacy option.')], default=1)
    request_email = StringField(
        u'Email', validators=[Email('Please enter a valid email address')])
    request_phone = PhoneNumberField(u'Phone Number')
    request_fax = PhoneNumberField(u'Fax Number')
    request_address_street = StringField(u'Street Address')
    request_address_city = StringField(u'City')
    request_address_state = SelectField(u'State', choices=states , default='NY')
    request_address_zip = StringField(u'Zip Code', validators=[Length(5, 5, 'Please enter the your five-digit zip code')])
    terms_of_use = BooleanField(u'I acknowledge that I have read and accepted the Terms of Use for this application, as stated above', validators=[DataRequired('You must accept the terms of use')])
    record_description = StringField(u'Attachment Description')
    record = FileField(u'Upload attachment')
    request_submit = SubmitField(u'Submit Request')


class NewRequestForm(Form):
    agency = db.session.query(models.Department).all()
    agencies = [('', '')]
    for d in agency:
        agencies.append((d.name, d.name))
    agencies.append(('Unknown', 'I Don\'t Know'))
    request_text = TextAreaField(u'Request Description*', validators=[
        DataRequired('The request description is required'),
        Length(1, 5000, 'Your request must be less than 5000 characters')])
    request_department = SelectField(u'Request Department*', choices=agencies,
                                     validators=[DataRequired('Please choose a department')], default='')
    request_first_name = StringField(
        u'First Name*', validators=[DataRequired('Please enter the requestor\'s first name')])
    request_last_name = StringField(
        u'Last Name*', validators=[DataRequired('Please enter the requestor\'s last name')])
    request_privacy = SelectField(u'Privacy Options', choices=[
        (1, 'Name and Request Description Public'),
        (2, 'Only Request Description Public'),
        (4, 'Only Name Public'),
        (8, 'Everything is Private')],
        validators=[DataRequired('You must select a privacy option.')], default=1)
    request_email = StringField(
        u'Email', validators=[Email('Please enter a valid email address')])
    request_phone = PhoneNumberField(u'Phone Number')
    request_fax = PhoneNumberField(u'Fax Number')
    request_address_street = StringField(u'Street Address')
    request_address_city = StringField(u'City')
    request_address_state = SelectField(u'State', choices=[
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ',
                                              'Arizona'), ('AR', 'Arkansas'),
        ('CA', 'California'), ('CO', 'Colorado'), ('CT',
                                                   'Connecticut'), ('DE', 'Delaware'),
        ('DC', 'District Of Columbia'), ('FL',
                                         'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'),
        ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'),
        ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA',
                                               'Louisiana'), ('ME', 'Maine'),
        ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI',
                                                      'Michigan'), ('MN', 'Minnesota'),
        ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT',
                                                    'Montana'), ('NE', 'Nebraska'),
        ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ',
                                                    'New Jersey'), ('NM', 'New Mexico'),
        ('NY', 'New York'), ('NC', 'North Carolina'), ('ND',
                                                       'North Dakota'), ('OH', 'Ohio'),
        ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA',
                                               'Pennsylvania'), ('RI', 'Rhode Island'),
        ('SC', 'South Carolina'), ('SD',
                                   'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'),
        ('UT', 'Utah'), ('VT', 'Vermont'), ('VA',
                                            'Virginia'), ('WA', 'Washington'),
        ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming')], default='NY')
    request_address_zip = StringField(u'Zip Code', validators=[
        Length(5, 5, 'Please enter the five-digit zip code')])
    recaptcha = ReCaptcha(app)
    terms_of_use = BooleanField(u'I acknowledge that I have read and accepted the Terms of Use for '
                                u'this application, as stated above',
                                validators=[DataRequired('You must accept the terms of use')])
    record_description = StringField(u'Attachment Description')
    record = FileField(u'Upload attachment')
    request_submit = SubmitField(u'Submit Request')


class LoginForm(Form):
    username = StringField('Email', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')
