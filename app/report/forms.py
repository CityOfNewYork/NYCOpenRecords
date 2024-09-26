"""
.. module:: report.forms.

    :synopsis: Defines forms used for report statistics.
"""
from datetime import date, timedelta

from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from wtforms.validators import DataRequired

from app.lib.db_utils import get_agency_choices
from app.constants.dates import MONTHS, PORTAL_START_YEAR


class ReportFilterForm(FlaskForm):
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


class AcknowledgmentForm(FlaskForm):
    """Form to generate a report with acknowledgment data."""
    date_from = DateField('Date From (required)', format='%m/%d/%Y', validators=[DataRequired()])
    date_to = DateField('Date To (required)', format='%m/%d/%Y', validators=[DataRequired()])
    submit_field = SubmitField('Generate Report')

    def validate(self):
        if not super().validate():
            return False
        is_valid = True
        for field in [self.date_from, self.date_to]:
            if field.data > date.today():
                field.errors.append('The {} cannot be greater than today.'.format(field.label.text))
                is_valid = False
        if self.date_to.data < self.date_from.data:
            field.errors.append('Date To cannot be before Date From.')
            is_valid = False
        if self.date_from.data == self.date_to.data:
            field.errors.append('The dates cannot be the same.')
            is_valid = False
        return is_valid


class MonthlyMetricsReportForm(FlaskForm):
    """Form to generate a monthly metrics report."""
    year = SelectField('Year (required)', choices=None, validators=[DataRequired()])
    month = SelectField('Month (required)', choices=MONTHS, validators=[DataRequired()])
    submit_field = SubmitField('Generate Report')

    def __init__(self):
        super(MonthlyMetricsReportForm, self).__init__()
        # Calculate years portal has been active
        years_active = []
        for year in range(date.today().year, PORTAL_START_YEAR-1, -1):
            years_active.append((str(year), str(year)))
        self.year.choices = years_active
        self.year.choices.insert(0, ('', ''))


class OpenDataReportForm(FlaskForm):
    """Form to generate a report with Open Data compliance data."""
    date_from = DateField('Date From (required)', id='open-data-date-from', format='%m/%d/%Y', validators=[DataRequired()])
    date_to = DateField('Date To (required)', id='open-data-date-to', format='%m/%d/%Y', validators=[DataRequired()])
    submit_field = SubmitField('Generate Report')

    def validate(self):
        if not super().validate():
            return False
        is_valid = True
        for field in [self.date_from, self.date_to]:
            if field.data > date.today():
                field.errors.append('The {} cannot be greater than today.'.format(field.label.text))
                is_valid = False
        if self.date_to.data < self.date_from.data:
            field.errors.append('Date To cannot be before Date From.')
            is_valid = False
        if self.date_from.data == self.date_to.data:
            field.errors.append('The dates cannot be the same.')
            is_valid = False
        if self.date_from.data + timedelta(days=365) < self.date_to.data:
            field.errors.append('Date From and Date To must be within one year.')
            is_valid = False
        return is_valid
