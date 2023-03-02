"""
.. module:: request.forms.

    :synopsis: Defines forms used to create FOIL requests.
"""

from datetime import datetime

from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    StringField,
    SelectField,
    TextAreaField,
    SubmitField,
    DateTimeField,
    SelectMultipleField,
)
from wtforms.validators import Email, Length, InputRequired
from sqlalchemy import or_, asc
from app.agency.api.utils import get_active_users_as_choices
from app.constants import (
    CATEGORIES,
    STATES,
    submission_methods,
    determination_type,
    response_type,
)
from app.lib.db_utils import get_agency_choices
from app.models import Reasons, LetterTemplates, EnvelopeTemplates, CustomRequestForms
from app.lib.recaptcha_utils import Recaptcha3Field


class PublicUserRequestForm(FlaskForm):
    """
    Form for public users to create a new FOIL request.
    For a public user, the required fields are:

    # Request information
    agency: agency selected for the request
    title: name or title of the request
    description: detailed description of the request

    """

    # Request Information
    request_category = SelectField("Category (optional)", choices=CATEGORIES)
    request_agency = SelectField("Agency (required)", choices=None)
    request_title = StringField("Request Title (required)")
    request_type = SelectField("Request Type (required)", choices=[])
    request_description = TextAreaField("Request Description (required)")

    # File Upload
    request_file = FileField("Upload File (optional, must be less than 20 Mb)")

    recaptcha = Recaptcha3Field(action="TestAction", execute_on_load=True)

    # Submit Button
    submit = SubmitField("Submit Request")

    def __init__(self):
        super(PublicUserRequestForm, self).__init__()
        self.request_agency.choices = get_agency_choices()
        self.request_agency.choices.insert(0, ("", ""))


class AgencyUserRequestForm(FlaskForm):
    """
    Form for agency users to create a new FOIL request.
    For an agency user, the required fields are:

    # Request Information
    agency: agency selected for the request
    title: name or title of the request
    description: detailed description of the request
    request_date: date the request was made
    method_received: format the request was received

    # Personal Information
    first_name: first name of the requester
    last_name: last name of the requester

    # Contact Information (at least one form on contact is required)
    email: requester's email address
    phone: requester's phone number
    fax: requester's fax number
    address, city, state, zip: requester's address
    """

    # Request Information
    request_agency = SelectField("Agency (required)", choices=None)
    request_type = SelectField("Request Type (required)", choices=[])
    request_title = StringField("Request Title (required)")
    request_description = TextAreaField("Request Description (required)")
    request_date = DateTimeField(
        "Date (required)", format="%m/%d/%Y", default=datetime.today
    )

    # Personal Information
    # TODO: when refactoring these classes, include length and other validators
    first_name = StringField("First Name (required)")
    last_name = StringField("Last Name (required)")
    user_title = StringField("Title")
    user_organization = StringField("Organization")

    # Contact Information
    email = StringField("Email")
    phone = StringField("Phone")
    fax = StringField("Fax")
    address = StringField("Address Line 1")
    address_two = StringField("Address Line 2")
    city = StringField("City")
    state = SelectField("State / U.S. Territory", choices=STATES, default="NY")
    zipcode = StringField("Zip")

    # Method Received
    method_received = SelectField(
        "Format Received (required)", choices=submission_methods.AS_CHOICES
    )

    # File Upload
    request_file = FileField("Upload File (optional, must be less than 20 Mb)")

    recaptcha = Recaptcha3Field(action="TestAction", execute_on_load=True)

    # Submit Button
    submit = SubmitField("Submit Request")

    def __init__(self):
        super(AgencyUserRequestForm, self).__init__()
        if len(current_user.agencies.all()) > 1:
            self.request_agency.choices = current_user.agencies_for_forms()


class AnonymousRequestForm(FlaskForm):
    """
    Form for anonymous users to create a new FOIL request.
    For a anonymous user, the required fields are:

    # Request Information
    agency: agency selected for the request
    title: name or title of the request
    description: detailed description of the request

    # Personal Information
    first_name: first name of the requester
    last_name: last name of the requester

    # Contact Information (at least one form on contact is required)
    email: requester's email address
    phone: requester's phone number
    fax: requester's fax number
    address, city, state, zip: requester's address
    """

    # Request Information
    request_category = SelectField("Category (optional)", choices=CATEGORIES)
    request_agency = SelectField("Agency (required)", choices=None)
    request_type = SelectField("Request Type (required)", choices=[])
    request_title = StringField("Request Title (required)")
    request_description = TextAreaField("Request Description (required)")

    # Personal Information
    first_name = StringField("First Name (required)")
    last_name = StringField("Last Name (required)")
    user_title = StringField("Title")
    user_organization = StringField("Organization")

    # Contact Information
    email = StringField("Email")
    phone = StringField("Phone")
    fax = StringField("Fax")
    address = StringField("Address Line 1")
    address_two = StringField("Address Line 2")
    city = StringField("City")
    state = SelectField("State / U.S. Territory", choices=STATES, default="NY")
    zipcode = StringField("Zip")

    # File Upload
    request_file = FileField("Upload File (optional, must be less than 20 Mb)")

    recaptcha = Recaptcha3Field(action="TestAction", execute_on_load=True)
    submit = SubmitField("Submit Request")

    def __init__(self):
        super(AnonymousRequestForm, self).__init__()
        self.request_agency.choices = get_agency_choices()
        self.request_agency.choices.insert(0, ("", ""))


class EditRequesterForm(FlaskForm):
    # TODO: Add class docstring
    email = StringField("Email")
    phone = StringField("Phone Number")
    fax = StringField("Fax Number")
    address_one = StringField("Address Line 1")
    address_two = StringField("Address Line 2")
    city = StringField("City")
    state = SelectField("State / U.S. Territory", choices=STATES)
    zipcode = StringField("Zip Code")
    title = StringField("Title")
    organization = StringField("Organization")

    def __init__(self, requester):
        """
        :type requester: app.models.Users
        """
        super(EditRequesterForm, self).__init__()
        self.email.data = requester.email or ""
        self.phone.data = requester.phone_number or ""
        self.fax.data = requester.fax_number or ""
        self.title.data = requester.title or ""
        self.organization.data = requester.organization or ""
        if requester.mailing_address is not None:
            self.address_one.data = requester.mailing_address.get("address_one") or ""
            self.address_two.data = requester.mailing_address.get("address_two") or ""
            self.city.data = requester.mailing_address.get("city") or ""
            self.state.data = requester.mailing_address.get("state") or ""
            self.zipcode.data = requester.mailing_address.get("zip") or ""


class DeterminationForm(FlaskForm):
    # TODO: Add class docstring
    def __init__(self, agency_ein):
        super(DeterminationForm, self).__init__()

        agency_closings = [
            (reason.id, reason.title)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.CLOSING,
                Reasons.agency_ein == agency_ein,
            ).order_by(asc(Reasons.id))
        ]
        agency_denials = [
            (reason.id, reason.title)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.DENIAL,
                Reasons.agency_ein == agency_ein,
            ).order_by(asc(Reasons.id))
        ]
        agency_reopenings = [
            (reason.id, reason.title)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.REOPENING,
                Reasons.agency_ein == agency_ein,
            ).order_by(asc(Reasons.id))
        ]
        default_closings = [
            (reason.id, reason.title)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.CLOSING, Reasons.agency_ein == None
            ).order_by(asc(Reasons.id))
        ]
        default_denials = [
            (reason.id, reason.title)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.DENIAL, Reasons.agency_ein == None
            ).order_by(asc(Reasons.id))
        ]
        default_reopenings = [
            (reason.id, reason.title)
            for reason in Reasons.query.filter(
                Reasons.type == determination_type.REOPENING, Reasons.agency_ein == None
            ).order_by(asc(Reasons.id))
        ]

        if (
            determination_type.CLOSING in self.ultimate_determination_type
            and determination_type.DENIAL in self.ultimate_determination_type
        ):
            self.reasons.choices = (
                agency_closings + agency_denials + default_closings + default_denials
            )
        elif determination_type.DENIAL in self.ultimate_determination_type:
            self.reasons.choices = agency_denials + default_denials
        elif determination_type.REOPENING in self.ultimate_determination_type:
            self.reasons.choices = agency_reopenings + default_reopenings

    @property
    def reasons(self):
        """ SelectMultipleField or SelectField """
        raise NotImplementedError

    @property
    def ultimate_determination_type(self):
        """ Closing or Denial """
        raise NotImplementedError


class DenyRequestForm(DeterminationForm):
    # TODO: Add class docstring
    reasons = SelectMultipleField("Reasons for Denial (Choose 1 or more)")
    ultimate_determination_type = [determination_type.DENIAL]


class CloseRequestForm(DeterminationForm):
    # TODO: Add class docstring
    reasons = SelectMultipleField("Reasons for Closing (Choose 1 or more)")
    ultimate_determination_type = [
        determination_type.CLOSING,
        determination_type.DENIAL,
    ]


class ReopenRequestForm(DeterminationForm):
    # TODO: Add class docstring
    reasons = SelectField("Reason for Re-Opening")
    ultimate_determination_type = [determination_type.REOPENING]


class GenerateEnvelopeForm(FlaskForm):
    # TODO: Add class docstring
    template = SelectField("Template")
    recipient_name = StringField("Recipient Name")
    organization = StringField("Organization")
    address_one = StringField("Address Line One")
    address_two = StringField("Address Line Two")
    city = StringField("City")
    state = StringField("State")
    zipcode = StringField("Zip Code")

    def __init__(self, agency_ein, requester):
        """
        :type requester: app.models.Users
        """
        super(GenerateEnvelopeForm, self).__init__()
        self.template.choices = [
            (envelope_template.id, envelope_template.title)
            for envelope_template in EnvelopeTemplates.query.filter_by(
                agency_ein=agency_ein
            )
        ]
        self.recipient_name.data = requester.name or ""
        self.organization.data = requester.organization or ""
        if requester.mailing_address is not None:
            self.address_one.data = requester.mailing_address.get("address_one") or ""
            self.address_two.data = requester.mailing_address.get("address_two") or ""
            self.city.data = requester.mailing_address.get("city") or ""
            self.state.data = requester.mailing_address.get("state") or ""
            self.zipcode.data = requester.mailing_address.get("zip") or ""


class GenerateLetterForm(FlaskForm):
    # TODO: Add class docstring
    def __init__(self, agency_ein):
        super(GenerateLetterForm, self).__init__()
        self.letter_templates.choices = [
            (letter.id, letter.title)
            for letter in LetterTemplates.query.filter(
                LetterTemplates.type_.in_(self.letter_type),
                or_(
                    LetterTemplates.agency_ein == agency_ein,
                    LetterTemplates.agency_ein == None,
                ),
            )
        ]
        self.letter_templates.choices.insert(0, ("", ""))

    @property
    def letter_templates(self):
        """ SelectField """
        raise NotImplementedError

    @property
    def letter_type(self):
        """ Acknowledgement, Extension, """
        raise NotImplementedError


class GenerateAcknowledgmentLetterForm(GenerateLetterForm):
    # TODO: Add class docstring
    letter_templates = SelectField("Letter Templates")
    letter_type = [determination_type.ACKNOWLEDGMENT]


class GenerateDenialLetterForm(GenerateLetterForm):
    # TODO: Add class docstring
    letter_templates = SelectField("Letter Templates")
    letter_type = [determination_type.DENIAL]


class GenerateClosingLetterForm(GenerateLetterForm):
    # TODO: Add class docstring
    letter_templates = SelectField("Letter Templates")
    letter_type = [determination_type.CLOSING, determination_type.DENIAL]

    def __init__(self, agency_ein):
        super(GenerateClosingLetterForm, self).__init__(agency_ein)
        agency_closings = [
            (letter.id, letter.title)
            for letter in LetterTemplates.query.filter(
                LetterTemplates.type_ == determination_type.CLOSING,
                LetterTemplates.agency_ein == agency_ein,
            )
        ]
        agency_denials = [
            (letter.id, letter.title)
            for letter in LetterTemplates.query.filter(
                LetterTemplates.type_ == determination_type.DENIAL,
                LetterTemplates.agency_ein == agency_ein,
            )
        ]
        default_closings = [
            (letter.id, letter.title)
            for letter in LetterTemplates.query.filter(
                LetterTemplates.type_ == determination_type.CLOSING,
                LetterTemplates.agency_ein == None,
            )
        ]
        default_denials = [
            (letter.id, letter.title)
            for letter in LetterTemplates.query.filter(
                LetterTemplates.type_ == determination_type.DENIAL,
                LetterTemplates.agency_ein == None,
            )
        ]
        self.letter_templates.choices = (
            agency_closings + agency_denials + default_closings + default_denials
        )
        self.letter_templates.choices.insert(0, ("", ""))


class GenerateExtensionLetterForm(GenerateLetterForm):
    # TODO: Add class docstring
    letter_templates = SelectField("Letter Templates")
    letter_type = [determination_type.EXTENSION]


class GenerateReopeningLetterForm(GenerateLetterForm):
    # TODO: Add class docstring
    letter_templates = SelectField("Letter Templates")
    letter_type = [determination_type.REOPENING]


class GenerateResponseLetterForm(GenerateLetterForm):
    # TODO: Add class docstring
    letter_templates = SelectField("Letter Templates")
    letter_type = [response_type.LETTER]


class SearchRequestsForm(FlaskForm):
    # TODO: Add class docstring
    agency_ein = SelectField("Agency")
    agency_user = SelectField("User")
    request_type = SelectField("Request Type", choices=[])

    # category = SelectField('Category', get_categories())

    def __init__(self):
        super(SearchRequestsForm, self).__init__()
        self.agency_ein.choices = get_agency_choices()
        self.agency_ein.choices.insert(0, ("", "All"))
        if current_user.is_agency:
            self.agency_ein.default = current_user.default_agency_ein
            user_agencies = sorted(
                [
                    (agencies.ein, agencies.name)
                    for agencies in current_user.agencies
                    if agencies.ein != current_user.default_agency_ein
                ],
                key=lambda x: x[1],
            )
            default_agency = current_user.default_agency

            # set default value of agency select field to agency user's primary agency
            self.agency_ein.default = default_agency.ein
            self.agency_ein.choices.insert(
                1,
                self.agency_ein.choices.pop(
                    self.agency_ein.choices.index(
                        (default_agency.ein, default_agency.name)
                    )
                ),
            )

            # set secondary agencies to be below the primary
            for agency in user_agencies:
                self.agency_ein.choices.insert(
                    2,
                    self.agency_ein.choices.pop(self.agency_ein.choices.index(agency)),
                )

            # get choices for agency user select field
            if current_user.is_agency_admin():
                self.agency_user.choices = get_active_users_as_choices(
                    current_user.default_agency.ein
                )

            if current_user.is_agency_active() and not current_user.is_agency_admin():
                self.agency_user.choices = [
                    ("", "All"),
                    (current_user.get_id(), "My Requests"),
                ]
                self.agency_user.default = current_user.get_id()

            if default_agency.agency_features["custom_request_forms"]["enabled"]:
                self.request_type.choices = [
                    (custom_request_form.form_name, custom_request_form.form_name)
                    for custom_request_form in CustomRequestForms.query.filter_by(
                        agency_ein=default_agency.ein
                    ).order_by(asc(CustomRequestForms.category), asc(CustomRequestForms.id)).all()
                ]
                self.request_type.choices.insert(0, ("", "All"))

            # process form for default values
            self.process()


class ContactAgencyForm(FlaskForm):
    # TODO: Add class docstring
    first_name = StringField(
        u"First Name", validators=[InputRequired(), Length(max=32)]
    )
    last_name = StringField(u"Last Name", validators=[InputRequired(), Length(max=64)])
    email = StringField(
        u"Email", validators=[InputRequired(), Length(max=254), Email()]
    )
    subject = StringField(u"Subject")
    message = TextAreaField(u"Message", validators=[InputRequired(), Length(max=5000)])
    submit = SubmitField(u"Send")

    def __init__(self, request):
        super(ContactAgencyForm, self).__init__()
        if current_user == request.requester:
            self.first_name.data = request.requester.first_name
            self.last_name.data = request.requester.last_name
            self.email.data = (
                request.requester.notification_email or request.requester.email
            )
        self.subject.data = "Inquiry about {}".format(request.id)


class TechnicalSupportForm(FlaskForm):
    recaptcha = Recaptcha3Field(action="TestAction", execute_on_load=True)