"""
.. module:: report.forms.

    :synopsis: Defines forms used for report statistics.
"""
from flask_wtf import Form
from wtforms import SelectField

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
