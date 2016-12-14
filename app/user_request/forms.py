from flask_wtf import Form
from wtforms import SelectField


class RemoveUserRequestForm(Form):
    user = SelectField('Users')

    def __init__(self, assigned_users):
        super(RemoveUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, '{} ({})'.format(agency_user.name, agency_user.email))
            for agency_user in assigned_users
        ]


class AddUserRequestForm(Form):
    user = SelectField('Users', choices=None)
    permission = SelectField('Users', choices=None)

    def __init__(self, active_users):
        super(AddUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, '{} ({})'.format(agency_user.name, agency_user.email))
            for agency_user in active_users
        ]

