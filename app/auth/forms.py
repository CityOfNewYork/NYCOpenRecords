"""

.. module:: auth.forms

    :synopsis: Defines the forms used to manage Authentication requests
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, SubmitField
from wtforms.validators import Length, Email, Optional, DataRequired

from app.constants import STATES


class StripFieldsForm(FlaskForm):
    """
    Any field data that can be stripped, will be stripped.
    http://stackoverflow.com/questions/26232165/automatically-strip-all-values-in-wtforms
    """

    class Meta:
        def bind_field(self, form, unbound_field, options):
            filters = unbound_field.kwargs.get("filters", [])
            filters.append(strip_filter)
            return unbound_field.bind(form=form, filters=filters, **options)


def strip_filter(value):
    if value is not None and hasattr(value, "strip"):
        return value.strip()
    return value


class ManageUserAccountForm(StripFieldsForm):
    """
    This form manages the OpenRecords specific account fields for a user account:
        Title: The job title for the user (e.g. Reporter); This is optional
        Organization: The company for the user (e.g. New York Times); This is optional
        Notification Email: The email to send OpenRecords notifications to
        Phone Number: The user's phone number; This is optional
        Fax Number: The user's fax number: This is optional
        Mailing Address: The user's mailing address; Optional;
            Format: Address One, Address Two, City, State, Zip (5 Digits)
    """

    title = StringField("Title", validators=[Length(max=64), Optional()])
    organization = StringField("Organization", validators=[Length(max=254), Optional()])
    notification_email = StringField(
        "Notification Email", validators=[Email(), Length(max=254), Optional()]
    )
    phone_number = StringField("Phone", validators=[Length(min=10, max=25), Optional()])
    fax_number = StringField("Fax", validators=[Length(min=10, max=25), Optional()])
    address_one = StringField("Line 1", validators=[Optional()])
    address_two = StringField("Line 2", validators=[Optional()])
    city = StringField("City", validators=[Optional()])
    state = SelectField(
        "State / U.S. Territory", choices=STATES, default="NY", validators=[Optional()]
    )
    zipcode = StringField(
        "Zip Code (5 Digits)", validators=[Length(min=5, max=5), Optional()]
    )

    submit = SubmitField("Update OpenRecords Account")

    def __init__(self, user=None):
        """
        :type user: app.models.Users
        """
        super(ManageUserAccountForm, self).__init__()
        self.user = user

    def autofill(self):
        if self.user is not None:
            self.title.data = self.user.title
            self.organization.data = self.user.organization
            self.notification_email.data = (
                self.user.notification_email or self.user.email
            )
            self.phone_number.data = self.user.phone_number
            self.fax_number.data = self.user.fax_number
            if self.user.mailing_address is not None:
                self.address_one.data = self.user.mailing_address.get("address_one")
                self.address_two.data = self.user.mailing_address.get("address_two")
                self.city.data = self.user.mailing_address.get("city")
                self.state.data = self.user.mailing_address.get("state")
                self.zipcode.data = self.user.mailing_address.get("zip")

    def validate(self):
        """ One mthod of contact must be provided. """
        base_is_valid = super(ManageUserAccountForm, self).validate()
        return base_is_valid and bool(
            self.notification_email.data
            or self.phone_number.data
            or self.fax_number.data
            or (  # mailing address
                self.address_one.data
                and self.city.data
                and self.state.data
                and self.zipcode.data
            )
        )


class ManageAgencyUserAccountForm(StripFieldsForm):
    """
    This form manages the OpenRecords specific account fields for a user account:
        Title: The job title for the user (e.g. Reporter); This is optional
        Organization: The company for the user (e.g. New York Times); This is optional
        Notification Email: The email to send OpenRecords notifications to
        Phone Number: The user's phone number; This is optional
        Fax Number: The user's fax number: This is optional
        Mailing Address: The user's mailing address; Optional;
            Format: Address One, Address Two, City, State, Zip (5 Digits)
    """

    default_agency = SelectField("Primary Agency", validators=[DataRequired()])
    title = StringField("Title", validators=[Length(max=64), Optional()])
    organization = StringField("Organization", validators=[Length(max=254), Optional()])
    notification_email = StringField(
        "Notification Email", validators=[Email(), Length(max=254), Optional()]
    )
    phone_number = StringField("Phone", validators=[Length(min=10, max=25), Optional()])
    fax_number = StringField("Fax", validators=[Length(min=10, max=25), Optional()])
    address_one = StringField("Line 1", validators=[Optional()])
    address_two = StringField("Line 2", validators=[Optional()])
    city = StringField("City", validators=[Optional()])
    state = SelectField(
        "State / U.S. Territory", choices=STATES, default="NY", validators=[Optional()]
    )
    zipcode = StringField(
        "Zip Code (5 Digits)", validators=[Length(min=5, max=5), Optional()]
    )

    submit = SubmitField("Update OpenRecords Account")

    def __init__(self, user=None):
        """
        :type user: app.models.Users
        """
        super(ManageAgencyUserAccountForm, self).__init__()
        self.user = user
        self.default_agency.choices = self.user.agencies_for_forms()

    def autofill(self):
        if self.user is not None:
            self.title.data = self.user.title
            self.organization.data = self.user.organization
            self.notification_email.data = (
                self.user.notification_email or self.user.email
            )
            self.phone_number.data = self.user.phone_number
            self.fax_number.data = self.user.fax_number
            if self.user.mailing_address is not None:
                self.address_one.data = self.user.mailing_address.get("address_one")
                self.address_two.data = self.user.mailing_address.get("address_two")
                self.city.data = self.user.mailing_address.get("city")
                self.state.data = self.user.mailing_address.get("state")
                self.zipcode.data = self.user.mailing_address.get("zip")

    def validate(self):
        """ One mthod of contact must be provided. """
        base_is_valid = super(ManageAgencyUserAccountForm, self).validate()
        return base_is_valid and bool(
            self.notification_email.data
            or self.phone_number.data
            or self.fax_number.data
            or (  # mailing address
                self.address_one.data
                and self.city.data
                and self.state.data
                and self.zipcode.data
            )
        )


class BasicLoginForm(FlaskForm):
    email = StringField("Email")
    password = PasswordField("Password")

    login = SubmitField("Login")
