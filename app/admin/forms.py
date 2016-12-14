from app.models import Agencies
from flask_wtf import Form
from wtforms import SelectField


class ActivateAgencyUserForm(Form):
    users = SelectField('Add Agency Users')

    def __init__(self, agency_ein):
        super(ActivateAgencyUserForm, self).__init__()
        self.users.choices = [
            (u.get_id(), '{} ( {} )'.format(u.name, u.email))
            for u in Agencies.query.filter_by(ein=agency_ein).one().inactive_users]


class SelectAgencyForm(Form):
    agencies = SelectField('Current Agency')

    def __init__(self, current_agency_ein=None):
        super(SelectAgencyForm, self).__init__()
        self.agencies.choices = [
            (a.ein, '({}) {}'.format('ACTIVE', a.name) if a.is_active else a.name)
            for a in Agencies.query.order_by(Agencies.is_active.desc(),
                                             Agencies.name.asc())]
        if current_agency_ein is not None:
            self.agencies.default = current_agency_ein
            self.process()
