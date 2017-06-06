from app.models import Agencies
from flask_wtf import Form
from wtforms import SelectField
from flask_login import current_user


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
            user_agencies = sorted([(agencies.ein, agencies.name)
                                    for agencies in current_user.agencies],
                                   key=lambda x: x[1])
            for user_agency in user_agencies:
                try:
                    self.agencies.choices.insert(0, self.agencies.choices.pop(self.agencies.choices.index(user_agency)))
                except ValueError:
                    self.agencies.choices.insert(0, self.agencies.choices.pop(
                        self.agencies.choices.index(
                            (user_agency[0], '(ACTIVE) {agency_name}'.format(agency_name=user_agency[1])))))
            self.process()

# TODO: Add forms to modify agency_features (see models.py:183)
