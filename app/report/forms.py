"""
.. module:: report.forms.

    :synopsis: Defines forms used for report statistics.
"""
from flask_login import current_user
from flask_wtf import Form
from wtforms import SelectField, DateField, SubmitField
from wtforms.validators import DataRequired

from app.lib.db_utils import get_agency_choices


class ReportFilterForm(Form):
    """
    Form for users to filter different report statistics.

    agency: agency selected to filter by
    user: active agency user selected to filter by
    """
    agency = SelectField('Agency Filter', choices=None)
    user = SelectField('Agency User Filter', choices=None)

    def __init__(self):
        super(ReportFilterForm, self).__init__()
        self.agency.choices = get_agency_choices()
        self.agency.choices.insert(0, ('all', 'All'))
        self.user.choices = []
        if current_user.is_agency:
            user_agencies = sorted([(agencies.ein, agencies.name)
                                    for agencies in current_user.agencies],
                                   key=lambda x: x[1])
            for user_agency in user_agencies:
                self.agency.choices.insert(1, self.agency.choices.pop(self.agency.choices.index(user_agency)))


class AcknowledgmentForm(Form):
    """
    """
    date_from = DateField('Date From (required)', format='%m/%d/%Y', validators=[DataRequired()])
    date_to = DateField('Date To (required)', format='%m/%d/%Y', validators=[DataRequired()])
    submit_field = SubmitField('Generate Report')
