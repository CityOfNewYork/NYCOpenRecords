from flask_wtf import Form
from wtforms import SelectField, SelectMultipleField
from app.constants import permission
from app.models import Roles


class AddUserRequestForm(Form):
    user = SelectField('Users', choices=None)
    permission = SelectMultipleField('Permissions', choices=None)
    roles = SelectField('Presets', choices=None)

    def __init__(self, assigned_users):
        super(AddUserRequestForm, self).__init__()
        self.user.choices = [
            (u.guid, '{} ({})'.format(u.name, u.email))
            for u in assigned_users
            ]
        self.user.choices.insert(0, (0, ''))
        self.user.default = self.user.choices[0]
        self.roles.choices = [
            (roles.id, roles.name) for roles in Roles.query.all()
            ]
        self.roles.choices.sort(key=lambda tup: tup[1])
        self.roles.default = Roles.query.filter_by(name='Anonymous User').one().id
        self.process()
        self.permission.choices = [
            (i, p.label) for i, p in enumerate(permission.ALL)
            ]


class EditUserRequestForm(Form):
    user = SelectField('Users', choices=None)
    permission = SelectMultipleField('Permissions', choices=None)
    roles = SelectField('Presets', choices=None)

    def __init__(self, assigned_users):
        super(EditUserRequestForm, self).__init__()
        self.user.choices = [
            (u.guid, '{} ({})'.format(u.name, u.email))
            for u in assigned_users
            ]
        self.user.choices.insert(0, (0, ''))
        self.user.default = self.user.choices[0]
        self.roles.choices = [
            (roles.id, roles.name) for roles in Roles.query.all()
            ]
        self.roles.choices.sort(key=lambda tup: tup[1])
        self.roles.default = Roles.query.filter_by(name='Anonymous User').one().id
        self.process()
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
