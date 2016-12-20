from flask_wtf import Form
from wtforms import SelectField

from app.lib.db_utils import get_agency_choices


class ReportFilterForm(Form):
    agency = SelectField('Agency Filter', choices=None)

    def __init__(self):
        super(ReportFilterForm, self).__init__()
        self.agency.choices = get_agency_choices()
        self.agency.choices.insert(0, ('', ''))
