"""
.. module:: request.forms.

    :synopsis: Defines forms used to create Procurement requests.
"""

from flask_wtf import Form
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from flask_wtf.file import FileField
from wtforms.validators import DataRequired, Length
from app.constants import categories, agencies, submission_method


class NewRequestForm(Form):
    """Form for creating a new FOIL request"""
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
    request_submission = SelectField(u'Submission Method*', choices=submission_method,
                                     validators=[DataRequired('Please select the submission method')])
    request_file = FileField()
    request_submit = SubmitField(u'Submit Request')
