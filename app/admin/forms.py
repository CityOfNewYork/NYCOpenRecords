from app.models import Agencies
from flask_wtf import Form
from wtforms import SelectField


class AddAgencyUserForm(Form):
    users = SelectField('Add Agency Users')

    def __init__(self, agency_ein):
        super(AddAgencyUserForm, self).__init__()
        self.users.choices = [(u.get_id(), '{} ( {} )'.format(u.name, u.email))
                              for u in Agencies.query.filter_by(ein=agency_ein).one().inactive_users]
