from flask import Flask
from flask_wtf import Form
from wtforms import StringField, SelectField, TextAreaField, BooleanField, SubmitField, FileField
from wtforms.validators import DataRequired, Length
app = Flask(__name__)

agencies = [
    ('', ''),
    ('Agency1', 'Agency1'),
    ('Agency2', 'Agency2'),
    ('Agency3', 'Agency3'),
    ('Agency4', 'Agency4'),
    ('Agency5', 'Agency5'),
    ('Agency6', 'Agency6'),
    ('Agency7', 'Agency7'),
    ('Agency8', 'Agency8')
]

categories = [
    ('', ''),
    ('Business', 'Business'),
    ('Civic Services', 'Civic Services'),
    ('Culture & Recreation', 'Culture & Recreation'),
    ('Education', 'Education'),
    ('Government Administration', 'Government Administration'),
    ('Environment', 'Environment'),
    ('Health', 'Health'),
    ('Housing & Development', 'Housing & Development'),
    ('Public Safety', 'Public Safety'),
    ('Social Services', 'Social Services'),
    ('Transportation', 'Transportation')
]


class NewRequestForm(Form):
    request_category = SelectField(u'Category*', choices=categories)
    request_agency = SelectField(u'Agency*', choices=agencies, validators=[
        DataRequired('Please select an agency')],
                                 default='')
    request_title = StringField(u'Request Title*', validators=[DataRequired('You must enter a summary of your request'),
                                                               Length(1, 250, 'Your summary must be less than 250'
                                                                              'characters')])
    request_description = TextAreaField(u'Detailed Description*',
                                        validators=[DataRequired('You must enter a description of your request'),
                                        Length(1, 5001, 'The detailed description of this request must be less than '
                                                        '5000 characters')])
    request_file = FileField()
    request_submit = SubmitField(u'Submit Request')
