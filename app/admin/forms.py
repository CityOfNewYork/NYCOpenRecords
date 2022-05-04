from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import (
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    Length,
    Email,
    DataRequired
)

from app.lib.db_utils import get_agency_choices
from app.models import Agencies


class ActivateAgencyUserForm(FlaskForm):
    users = SelectField('Add Agency Users')

    def __init__(self, agency_ein):
        super(ActivateAgencyUserForm, self).__init__()
        self.users.choices = [
            (u.get_id(), '{} ( {} )'.format(u.name, u.email))
            for u in Agencies.query.filter_by(ein=agency_ein).one().inactive_users]


class SelectAgencyForm(FlaskForm):
    agencies = SelectField('Current Agency')

    def __init__(self, agency_ein=None):
        super(SelectAgencyForm, self).__init__()

        if current_user.is_super:
            # Super Users will always see every agency in the dropdown.
            self.agencies.choices = [
                (
                    agency.ein,
                    '({status}) {agency_name}'.format(
                        status='ACTIVE',
                        agency_name=agency.name
                    ) if agency.is_active else
                    '{agency_name}'.format(
                        agency_name=agency.name
                    )
                )
                for agency in Agencies.query.order_by(Agencies.is_active.desc(),
                                                      Agencies._name.asc()).all()
            ]
        else:
            # Multi-Agency Admin Users will only see the agencies that they administer in the dropdown.
            agency_choices = []
            for agency in current_user.agencies.order_by(Agencies.is_active.desc(), Agencies._name.asc()).all():
                if current_user.is_agency_admin(agency.ein):
                    agency_tuple = (agency.ein,
                                    '({status}) {agency_name}'.format(
                                        status='ACTIVE',
                                        agency_name=agency.name
                                    ) if agency.is_active else
                                    '{agency_name}'.format(
                                        agency_name=agency.name)
                                    )
                    agency_choices.append(agency_tuple)
            self.agencies.choices = agency_choices
        if agency_ein:
            for agency in self.agencies.choices:
                if agency[0] == agency_ein:
                    self.agencies.choices.insert(0, self.agencies.choices.pop(self.agencies.choices.index(agency)))
        self.process()


# TODO: Add forms to modify agency_features (see models.py:183)


class AddAgencyUserForm(FlaskForm):
    agency = SelectField('Agency', choices=None, validators=[DataRequired()])
    first_name = StringField('First Name', validators=[Length(max=32), DataRequired()])
    last_name = StringField('Last Name', validators=[Length(max=64), DataRequired()])
    email = StringField('Email', validators=[Email(), Length(max=254), DataRequired()])
    submit = SubmitField('Add User')

    def __init__(self):
        super(AddAgencyUserForm, self).__init__()
        self.agency.choices = get_agency_choices()
        self.agency.choices.insert(0, ('', ''))
