from flask_wtf import Form
from wtforms import SelectField
from app.constants import permission

class AddUserRequestForm(Form):
    user = SelectField('Users', choices=None)
    permission = SelectField('Permissions', choices=None)

    def __init__(self, active_users):
        super(AddUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, '{} ({})'.format(agency_user.name, agency_user.email))
            for agency_user in active_users
            ]


class EditUserRequestForm(Form):
    user = SelectField('Users', choices=None)
    permission = SelectField('Users', choices=None)

    def __init__(self, active_users):
        super(EditUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, '{} ({})'.format(agency_user.name, agency_user.email))
            for agency_user in active_users
            ]
        self.permission.choices = [
            (i, p.label) for i, p in enumerate(permission.ALL)
        ]


class RemoveUserRequestForm(Form):
    user = SelectField('Users')

    def __init__(self, assigned_users):
        super(RemoveUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, '{} ({})'.format(agency_user.name, agency_user.email))
            for agency_user in assigned_users
            ]
