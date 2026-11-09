from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, BooleanField
from app.constants import permission, role_name
from app.models import Roles


class AddUserRequestForm(FlaskForm):
    user = SelectField('Users', choices=None)
    permission = SelectMultipleField('Permissions', choices=None)
    roles = SelectField('Presets', choices=None)
    point_of_contact = BooleanField()

    def __init__(self, assigned_users):
        super(AddUserRequestForm, self).__init__()
        self.user.choices = [
            (u.guid, '{} ({})'.format(u.name, u.email))
            for u in assigned_users
            ]
        self.user.choices.insert(0, (0, ''))
        self.user.default = self.user.choices[0]
        self.roles.choices = []
        for role in Roles.query.all():
            if role.name == role_name.AGENCY_ADMIN:
                self.roles.choices.append((role.id, 'Request Administrator'))
            else:
                self.roles.choices.append((role.id, role.name))
        self.roles.choices.sort(key=lambda tup: tup[1])
        self.roles.default = Roles.query.filter_by(name=role_name.ANONYMOUS).one().id
        self.process()
        self.permission.choices = [
            (i, p.label) for i, p in enumerate(permission.ALL)
            ]


class EditUserRequestForm(FlaskForm):
    user = SelectField('Users', choices=None)
    permission = SelectMultipleField('Permissions', choices=None)
    roles = SelectField('Presets', choices=None)
    point_of_contact = BooleanField()

    def __init__(self, assigned_users):
        super(EditUserRequestForm, self).__init__()
        self.user.choices = [
            (u.guid, '{} ({})'.format(u.name, u.email))
            for u in assigned_users
            ]
        self.user.choices.insert(0, (0, ''))
        self.user.default = self.user.choices[0]
        self.roles.choices = []
        for role in Roles.query.all():
            if role.name == role_name.AGENCY_ADMIN:
                self.roles.choices.append((role.id, 'Request Administrator'))
            else:
                self.roles.choices.append((role.id, role.name))
        self.roles.choices.insert(0, (0, ''))
        self.roles.choices.sort(key=lambda tup: tup[1])
        self.process()
        self.permission.choices = [
            (i, p.label) for i, p in enumerate(permission.ALL)
            ]


class RemoveUserRequestForm(FlaskForm):
    user = SelectField('Users')

    def __init__(self, assigned_users):
        super(RemoveUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, '{} ({})'.format(agency_user.name, agency_user.email))
            for agency_user in assigned_users
            ]
