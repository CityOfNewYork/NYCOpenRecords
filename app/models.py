"""
Models for OpenRecords database
"""
import csv
import json
from datetime import datetime

from flask import current_app
from flask_login import UserMixin, AnonymousUserMixin
from flask_login import current_user
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSON

from app import db
from app.constants import (
    PUBLIC_USER,
    AGENCY_USER,
    permission,
    role_name,
    request_status,
)


class Roles(db.Model):
    """
    Define the Roles class with the following columns and relationships:

    id -- Column: Integer, PrimaryKey
    name -- Column: String(64), Unique
    default -- Column: Boolean, Default = False
    permissions -- Column: Integer
    users -- Relationship: 'User', 'role'
    """
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permissions = db.Column(db.Integer)

    @classmethod
    def populate(cls):
        """
        Insert permissions for each role.
        """
        roles = {
            role_name.ANONYMOUS: (
                permission.DUPLICATE_REQUEST |
                permission.VIEW_REQUEST_STATUS_PUBLIC |
                permission.VIEW_REQUEST_INFO_PUBLIC
            ),
            role_name.PUBLIC_NON_REQUESTER: (
                permission.ADD_NOTE |
                permission.DUPLICATE_REQUEST |
                permission.VIEW_REQUEST_STATUS_PUBLIC |
                permission.VIEW_REQUEST_INFO_PUBLIC
            ),
            role_name.PUBLIC_REQUESTER: (
                permission.ADD_NOTE |
                permission.UPLOAD_DOCUMENTS |
                permission.VIEW_DOCUMENTS_IMMEDIATELY |
                permission.VIEW_REQUEST_INFO_ALL |
                permission.VIEW_REQUEST_STATUS_PUBLIC
            ),
            role_name.AGENCY_HELPER: (
                permission.ADD_NOTE |
                permission.UPLOAD_DOCUMENTS |
                permission.VIEW_REQUESTS_HELPER |
                permission.VIEW_REQUEST_INFO_ALL |
                permission.VIEW_REQUEST_STATUS_ALL
            ),
            role_name.AGENCY_OFFICER: (
                permission.ADD_NOTE |
                permission.UPLOAD_DOCUMENTS |
                permission.EXTEND_REQUESTS |
                permission.CLOSE_REQUESTS |
                permission.ADD_HELPERS |
                permission.REMOVE_HELPERS |
                permission.ACKNOWLEDGE |
                permission.VIEW_REQUESTS_AGENCY |
                permission.VIEW_REQUEST_INFO_ALL |
                permission.VIEW_REQUEST_STATUS_ALL
            ),
            role_name.AGENCY_ADMIN: (
                permission.ADD_NOTE |
                permission.UPLOAD_DOCUMENTS |
                permission.EXTEND_REQUESTS |
                permission.CLOSE_REQUESTS |
                permission.ADD_HELPERS |
                permission.REMOVE_HELPERS |
                permission.ACKNOWLEDGE |
                permission.CHANGE_REQUEST_POC |
                permission.VIEW_REQUESTS_ALL |
                permission.VIEW_REQUEST_INFO_ALL |
                permission.VIEW_REQUEST_STATUS_ALL
            )
        }

        for name, value in roles.items():
            role = Roles.query.filter_by(name=name).first()
            if role is None:
                role = cls(name=name)
            role.permissions = value
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Roles %r>' % self.name


class Agencies(db.Model):
    """
    Define the Agencies class with the following columns and relationships:

    ein - the primary key of the agencies table, 3 digit integer that is unique for each agency
    category - a string containing the category of the agency (ex: business/education)
    name - a string containing the name of the agency
    next_request_number - a sequence containing the next number for the request starting at 1, each agency has its own
                          request number sequence
    default_email - a string containing the default email of the agency regarding general inquiries about requests
    appeal_email - a string containing the appeal email for users regarding the agency closing or denying requests
    """

    __tablename__ = 'agencies'
    ein = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(256))
    name = db.Column(db.String(256), nullable=False)
    next_request_number = db.Column(db.Integer(), db.Sequence('request_seq'))
    default_email = db.Column(db.String(254))
    appeals_email = db.Column(db.String(254))

    @classmethod
    def populate(cls):
        """
        Automatically populate the agencies table for the OpenRecords application.
        """
        data = open(current_app.config['AGENCY_DATA'], 'r')
        dictreader = csv.DictReader(data)

        for row in dictreader:
            agency = cls(
                ein=row['ein'],
                category=row['category'],
                name=row['name'],
                next_request_number=row['next_request_number'],
                default_email=row['default_email'],
                appeals_email=row['appeals_email']
            )
            db.session.add(agency)
        db.session.commit()

    def __repr__(self):
        return '<Agencies %r>' % self.name


class Users(UserMixin, db.Model):
    """
    Define the Users class with the following columns and relationships:

    guid - a string that contains the unique guid of users
    user_type - a string that tells what type of a user they are (agency user, helper, etc.)
    guid and user_type are combined to create a composite primary key
    agency - a foreign key that links to the primary key of the agency table
    email - a string containing the user's email
    first_name - a string containing the user's first name
    middle_initial - a string containing the user's middle initial
    last_name - a string containing the user's last name
    email_validated - a boolean that is set to true if the user's email has been validated
    terms_of_use_accepted - a boolean that is set to true if the user has agreed to their agency's terms of use
    title - a string containing the user's title if they are affiliated with an outside company
    company - a string containing the user's outside company affiliation
    phone_number - string containing the user's phone number
    fax_number - string containing the user's fax number
    mailing_address - a JSON object containing the user's address
    """
    __tablename__ = 'users'
    guid = db.Column(db.String(64), primary_key=True)  # guid + user type
    user_type = db.Column(db.String(64), primary_key=True)
    agency = db.Column(db.Integer, db.ForeignKey('agencies.ein'))
    email = db.Column(db.String(254))
    first_name = db.Column(db.String(32), nullable=False)
    middle_initial = db.Column(db.String(1))
    last_name = db.Column(db.String(64), nullable=False)
    email_validated = db.Column(db.Boolean(), nullable=False)
    terms_of_use_accepted = db.Column(db.String(16), nullable=True)
    title = db.Column(db.String(64))
    organization = db.Column(db.String(128))  # Outside organization
    phone_number = db.Column(db.String(15))
    fax_number = db.Column(db.String(15))
    mailing_address = db.Column(JSON)  # need to define validation for minimum acceptable mailing address

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.email_validated and self.terms_of_use_accepted

    @property
    def is_public(self):
        """
        Checks to see if the current user is a public user as defined below:

        PUBLIC_USER_NYC_ID = 'EDIRSSO'
        PUBLIC_USER_FACEBOOK = 'FacebookSSO'
        PUBLIC_USER_LINKEDIN = 'LinkedInSSO'
        PUBLIC_USER_GOOGLE = 'GoogleSSO'
        PUBLIC_USER_YAHOO = 'YahooSSO'
        PUBLIC_USER_MICROSOFT = 'MSLiveSSO'

        :return: Boolean
        """
        return current_user.user_type in PUBLIC_USER

    @property
    def is_agency(self):
        """
        Checks to see if the current user is an agency user

        AGENCY_USER = 'Saml2In:NYC Employees'

        :return: Boolean
        """
        return current_user.user_type == AGENCY_USER

    def get_id(self):
        return "{}:{}".format(self.guid, self.user_type)

    def __init__(self, **kwargs):
        super(Users, self).__init__(**kwargs)

    def __repr__(self):
        return '<Users {}:{}>'.format(self.guid, self.user_type)


class Anonymous(AnonymousUserMixin):
    @property
    def is_authenticated(self):
        """
        Anonymous users are not authenticated.
        :return: Boolean
        """
        return False

    @property
    def is_public(self):
        """
        Anonymous users are treated differently from Public Users who are authenticated. This method always
        returns False.
        :return: Boolean
        """
        return False

    @property
    def is_anonymous(self):
        """
        Anonymous users always return True
        :return: Boolean
        """
        return True

    @property
    def is_agency(self):
        """
        Anonymous users always return False
        :return: Boolean
        """
        return False

    def get_id(self):
        return "{}:{}".format(self.guid, self.user_type)


class Requests(db.Model):
    """
    Define the Requests class with the following columns and relationships:

    id - a string containing the request id, of the form: FOIL - year 4 digits - EIN 3 digits - 5 digits for request number
    agency - a foreign key that links that the primary key of the agency the request was assigned to
    title - a string containing a short description of the request
    description - a string containing a full description of what is needed from the request
    date_created - the actual creation time of the request
    date_submitted - a date that rolls forward to the next business day based on date_created
    due_date - the date that is set five days after date_submitted, the agency has to acknowledge the request by the due date
    submission - a Enum that selects from a list of submission methods
    current_status - a Enum that selects from a list of different statuses a request can have
    privacy - a JSON object that contains the boolean privacy options of a request's title and agency description
              (True = Private, False = Public)
    """

    __tablename__ = 'requests'
    id = db.Column(db.String(19), primary_key=True)
    agency = db.Column(db.Integer, db.ForeignKey('agencies.ein'))
    title = db.Column(db.String(90))
    description = db.Column(db.String(5000))
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    date_submitted = db.Column(db.DateTime)  # used to calculate due date, rounded off to next business day
    due_date = db.Column(db.DateTime)
    submission = db.Column(
        db.String(30))  # direct input/mail/fax/email/phone/311/text method of answering request default is direct input
    current_status = db.Column(db.Enum(
        request_status.IN_PROGRESS,
        request_status.CLOSED,
        request_status.OPEN,
        request_status.DUE_SOON,  # within the next "5" business days
        request_status.RE_OPENED,
        request_status.OVERDUE,
        name='status'))
    privacy = db.Column(JSON)
    agency_description = db.Column(db.String(5000))

    # TODO: agency = db.relationship('Agencies', backref=db.backref('request', use_list=False))

    def __init__(
            self,
            id,
            title,
            description,
            agency,
            date_created,
            privacy=None,
            date_submitted=None,
            due_date=None,
            submission=None,
            current_status=None,
            agency_description=None
    ):
        privacy_default = {'title': 'false', 'agency_description': 'true'}
        self.id = id
        self.title = title
        self.description = description
        self.agency = agency
        self.date_created = date_created
        self.privacy = privacy or json.dumps(privacy_default)
        self.date_submitted = date_submitted
        self.due_date = due_date
        self.submission = submission
        self.current_status = current_status
        self.agency_description = agency_description

    def __repr__(self):
        return '<Requests %r>' % self.id

    def get_due_date(self):
        return self.due_date.strftime('%m/%d/%Y')


class Events(db.Model):
    """
    Define the Event class with the following columns and relationships:
    Events are any type of action that happened to a request after it was submitted

    id - an integer that is the primary key of an Events
    request_id - a foreign key that links to a request's primary key
    user_id - a foreign key that links to the user_id of the person who performed the event
    response_id - a foreign key that links to the primary key of a response
    type - a string containing the type of event that occurred
    timestamp - a datetime that keeps track of what time an event was performed
    previous_response_value - a string containing the old response value
    new_response_value - a string containing the new response value
    """

    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('requests.id'))
    user_id = db.Column(db.String(64))  # who did the action
    user_type = db.Column(db.String(64))
    response_id = db.Column(db.Integer, db.ForeignKey('responses.id'))
    type = db.Column(db.String(30))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    previous_response_value = db.Column(JSON)
    new_response_value = db.Column(JSON)

    __table_args__ = (ForeignKeyConstraint([user_id, user_type],
                                           [Users.guid, Users.user_type]),
                      {})

    def __repr__(self):
        return '<Events %r>' % self.id


class Responses(db.Model):
    """
    Define the Response class with the following columns and relationships:

    id - an integer that is the primary key of a Responses
    request_id - a foreign key that links to the primary key of a request
    type - a string containing the type of response that was given for a request
    date_modified - a datetime object that keeps track of when a request was changed
    content - a JSON object that contains the content for all the possible responses a request can have
    privacy - an Enum containing the privacy options for a response
    """

    __tablename__ = 'responses'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('requests.id'))
    type = db.Column(db.String(30))
    date_modified = db.Column(db.DateTime)
    metadata_id = db.Column(db.Integer)
    privacy = db.Column(db.Enum("private", "release_private", "release_public", name="privacy"))

    def __repr__(self):
        return '<Responses %r>' % self.id


class Reasons(db.Model):
    """
    Define the Reason class with the following columns and relationships:

    id - an integer that is the primary key of a Reasons
    agency - a foreign key that links to the a agency's primary key which is the EIN number
    deny_reason - a string containing the message that will be shown when a request is denied
    """

    __tablename__ = 'reasons'
    id = db.Column(db.Integer, primary_key=True)
    agency = db.Column(db.Integer, db.ForeignKey('agencies.ein'), nullable=True)
    deny_reason = db.Column(db.String)  # reasons for denying a request based off law dept's responses


class UserRequests(db.Model):
    """
    Define the UserRequest class with the following columns and relationships:
    A UserRequest is a many to many relationship between users who are related to a certain request
    user_guid and request_id are combined to create a composite primary key

    user_guid = a foreign key that links to the primary key of the User table
    request_id = a foreign key that links to the primary key of the Request table
    """

    __tablename__ = 'user_requests'
    user_guid = db.Column(db.String(64), primary_key=True)
    user_type = db.Column(db.String(64), primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey("requests.id"), primary_key=True)
    permissions = db.Column(db.Integer)

    __table_args__ = (ForeignKeyConstraint([user_guid, user_type],
                                           [Users.guid, Users.user_type]),
                      {})

    def has_permission(self, permission):
        """
        Ex:
            has_permission(permission.ADD_NOTE)
        """
        return bool(self.permissions & permission)


class Notes(db.Model):
    """
    Define the Notes class with the following columns and relationships:

    metadata_id - an integer that is the primary key of Notes
    content - a string that contains the content of a note
    """
    __tablename__ = 'notes'
    metadata_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(5000))


class Files(db.Model):
    """
    Define the Files class with the following columns and relationships:

    metadata_id - an integer that is the primary key of Files
    name - a string containing the name of a file (name is the secured filename)
    mime_type - a string containing the mime_type of a file
    title - a string containing the title of a file (user defined)
    size - a string containing the size of a file
    """
    __tablename__ = 'files'
    metadata_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)  # secured filename
    mime_type = db.Column(db.String)
    title = db.Column(db.String)
    size = db.Column(db.Integer)


class Links(db.Model):
    """
    Define the Links class with the following columns and relationships:

    metadata_id - an integer that is the primary key of Links
    title - a string containing the title of a link
    url - a string containing the url link
    """
    __tablename__ = 'links'
    metadata_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    url = db.Column(db.String)


class Instructions(db.Model):
    """
    Define the Instructions class with the following columns and relationships:

    metadata_id - an integer that is the primary key of Instructions
    content - a string containing the content of an instruction
    """
    __tablename__ = 'instructions'
    metadata_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String)


class Extensions(db.Model):
    """
    Define the Extensions class with the following columns and relationships:

    metadata_id - an integer that is the primary key of Extensions
    reason - a string containing the reason for an extension
    date - a datetime object containing the extended date of a request
    """
    __tablename__ = 'extensions'
    metadata_id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String)
    date = db.Column(db.DateTime)


class Emails(db.Model):
    """
    Define the Emails class with the following columns and relationships:

    metadata_id - an integer that is the primary key of Emails
    to - a string containing who the the email is being sent to
    cc - a string containing who is cc'd in an email
    bcc -  a string containing who is bcc'd in an email
    subject - a string containing the subject of an email
    email_content - a string containing the content of an email
    linked_files - an array of strings containing the links to the files
    """
    __tablename__ = 'emails'
    metadata_id = db.Column(db.Integer, primary_key=True)
    to = db.Column(db.String)
    cc = db.Column(db.String)
    bcc = db.Column(db.String)
    subject = db.Column(db.String(5000))
    email_content = db.Column(db.String)
    linked_files = db.Column(ARRAY(db.String))
