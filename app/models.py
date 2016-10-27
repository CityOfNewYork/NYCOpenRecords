"""
Models for OpenRecords database
"""
import csv
from datetime import datetime

from flask import current_app
from flask_login import UserMixin, AnonymousUserMixin
from flask_login import current_user
from sqlalchemy.dialects.postgresql import ARRAY, JSON

from app import db, es
from app.constants import (
    USER_ID_DELIMITER,
    permission,
    role_name,
    user_type_auth,
    user_type_request,
    request_status,
    response_privacy,
    submission_methods,
)
from app.search.constants import INDEX


class Roles(db.Model):
    """
    Define the Roles class with the following columns and relationships:

    Roles - Default sets of permissions

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
    administrators - an array of guid::auth_user_type strings that identify default admins for an agencies requests
    """
    __tablename__ = 'agencies'
    ein = db.Column(db.Integer, primary_key=True)  # FIXME: add length 3 if possible
    category = db.Column(db.String(256))
    name = db.Column(db.String(256), nullable=False)
    next_request_number = db.Column(db.Integer(), db.Sequence('request_seq'))
    default_email = db.Column(db.String(254))
    appeals_email = db.Column(db.String(254))
    administrators = db.Column(ARRAY(db.String))

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
    auth_user_type - a string that tells what type of a user they are (agency user, helper, etc.)
    guid and auth_user_type are combined to create a composite primary key
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
    guid = db.Column(db.String(64), primary_key=True)  # guid + auth_user_type
    auth_user_type = db.Column(
        db.Enum(user_type_auth.AGENCY_USER,
                user_type_auth.PUBLIC_USER_FACEBOOK,
                user_type_auth.PUBLIC_USER_MICROSOFT,
                user_type_auth.PUBLIC_USER_YAHOO,
                user_type_auth.PUBLIC_USER_LINKEDIN,
                user_type_auth.PUBLIC_USER_GOOGLE,
                user_type_auth.PUBLIC_USER_NYC_ID,
                user_type_auth.ANONYMOUS_USER,
                name='auth_user_type'),
        primary_key=True)
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
    user_requests = db.relationship("UserRequests", backref="user")

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
        return self.auth_user_type in user_type_auth.PUBLIC_USER_TYPES

    @property
    def is_agency(self):
        """
        Checks to see if the current user is an agency user

        AGENCY_USER = 'Saml2In:NYC Employees'

        :return: Boolean
        """
        return self.auth_user_type == user_type_auth.AGENCY_USER

    @property
    def is_anonymous_requester(self):
        """
        Checks to see if the current user is an anonymous requester

        NOTE: This is not the same as an anonymous user! This returns
        true if this user has been created for a specific request.

        :return: Boolean
        """
        return self.auth_user_type == user_type_auth.ANONYMOUS_USER

    def get_id(self):
        return USER_ID_DELIMITER.join((self.guid, self.auth_user_type))

    @property
    def name(self):
        return "{} {}".format(self.first_name, self.last_name)

    def __init__(self, **kwargs):
        super(Users, self).__init__(**kwargs)

    def __repr__(self):
        return '<Users {}>'.format(self.get_id())


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
    agency_ein = db.Column(db.Integer, db.ForeignKey('agencies.ein'))
    title = db.Column(db.String(90))
    description = db.Column(db.String(5000))
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    date_submitted = db.Column(db.DateTime)  # used to calculate due date, rounded off to next business day
    due_date = db.Column(db.DateTime)
    submission = db.Column(
        db.Enum(submission_methods.DIRECT_INPUT,
                submission_methods.FAX,
                submission_methods.PHONE,
                submission_methods.EMAIL,
                submission_methods.MAIL,
                submission_methods.IN_PERSON,
                submission_methods.THREE_ONE_ONE,
                name='submission'))
    current_status = db.Column(
        db.Enum(request_status.OPEN,
                request_status.IN_PROGRESS,
                request_status.DUE_SOON,  # within the next 5 business days
                request_status.OVERDUE,
                request_status.CLOSED,
                request_status.RE_OPENED,
                name='status'))
    privacy = db.Column(JSON)
    agency_description = db.Column(db.String(5000))

    user_requests = db.relationship('UserRequests', backref='request', lazy='dynamic')
    agency = db.relationship('Agencies', backref=db.backref('request', uselist=False))
    requester = db.relationship(
        'Users',
        secondary='user_requests',  # expects table name
        primaryjoin=lambda: Requests.id == UserRequests.request_id,
        secondaryjoin="and_(Users.guid == UserRequests.user_guid, "
                      "Users.auth_user_type == UserRequests.auth_user_type,"
                      "UserRequests.request_user_type == '{}')".format(
            user_type_request.REQUESTER),
        backref=db.backref('request', uselist=False),
        viewonly=True,
        uselist=False
    )

    PRIVACY_DEFAULT = {'title': False, 'agency_description': True}

    def __init__(
            self,
            id,
            title,
            description,
            agency_ein,
            date_created,
            privacy=None,
            date_submitted=None,
            due_date=None,
            submission=None,
            current_status=None,
            agency_description=None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.agency_ein = agency_ein
        self.date_created = date_created
        self.privacy = privacy or self.PRIVACY_DEFAULT
        self.date_submitted = date_submitted
        self.due_date = due_date
        self.submission = submission
        self.current_status = current_status
        self.agency_description = agency_description

    def get_formatted_due_date(self):
        return self.due_date.strftime('%m/%d/%Y')

    def es_update(self):
        result = es.update(
            index=INDEX,
            doc_type='request',
            id=self.id,
            body = {
                'doc': {
                    'title': self.title,
                    'description': self.description,
                    'agency_description': self.agency_description,
                    'title_private': self.privacy['title'],
                    'agency_description_private': self.privacy['agency_description'],
                    'date_due': self.due_date,
                    'submission': self.submission,
                    'status': self.current_status,
                    'public_title': 'Private' if self.privacy['title'] else self.title
                }
            },
            # refresh='wait_for'
        )
        import json
        print(json.dumps(result, indent=2))

    def es_create(self):
        """ Must be called AFTER UserRequest has been created. """
        es.create(
            index=INDEX,
            doc_type='request',
            id=self.id,
            body = {
                'title': self.title,
                'description': self.description,
                'agency_description': self.agency_description,
                'title_private': self.privacy['title'],
                'agency_description_private': self.privacy['agency_description'],
                'date_submitted': self.date_submitted,
                'date_due': self.due_date,
                'submission': self.submission,
                'status': self.current_status,
                'requester_id': (self.requester.get_id()
                                 if not self.requester.is_anonymous_requester
                                 else ''),
                'public_title': 'Private' if self.privacy['title'] else self.title,
            }
        )

    def __repr__(self):
        return '<Requests %r>' % self.id


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
    auth_user_type = db.Column(
        db.Enum(user_type_auth.AGENCY_USER,
                user_type_auth.PUBLIC_USER_FACEBOOK,
                user_type_auth.PUBLIC_USER_MICROSOFT,
                user_type_auth.PUBLIC_USER_YAHOO,
                user_type_auth.PUBLIC_USER_LINKEDIN,
                user_type_auth.PUBLIC_USER_GOOGLE,
                user_type_auth.PUBLIC_USER_NYC_ID,
                user_type_auth.ANONYMOUS_USER,
                name='auth_user_type'),
        primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('responses.id'))
    type = db.Column(db.String(30))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    previous_response_value = db.Column(JSON)
    new_response_value = db.Column(JSON)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [user_id, auth_user_type],
            [Users.guid, Users.auth_user_type]
        ),
    )


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
    type = db.Column(db.String(30))  # TODO: enum
    metadata_id = db.Column(db.Integer, db.ForeignKey('metadatas.id'), nullable=False)
    privacy = db.Column(db.Enum(
        response_privacy.PRIVATE,
        response_privacy.RELEASE_AND_PRIVATE,
        response_privacy.RELEASE_AND_PUBLIC,
        name="privacy"))
    date_modified = db.Column(db.DateTime)

    metadatas = db.relationship(  # 'metadata' is reserved
        'Metadatas', backref=db.backref('response', uselist=False))

    def __init__(self,
                 request_id,
                 type,
                 metadata_id,
                 privacy,
                 date_modified=datetime.utcnow()):
        self.request_id = request_id
        self.type = type
        self.metadata_id = metadata_id
        self.privacy = privacy
        self.date_modified = date_modified

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
    request_user_type: Defines a user by their relationship to the request.
        Requester submitted the request,
        Agency is a user from the agency to whom the request is assigned.
        Anonymous request_user_type is not needed, since anonymous users can always browse a request
            for public information.
    """
    __tablename__ = 'user_requests'
    user_guid = db.Column(db.String(64), primary_key=True)
    auth_user_type = db.Column(
        db.Enum(user_type_auth.AGENCY_USER,
                user_type_auth.PUBLIC_USER_FACEBOOK,
                user_type_auth.PUBLIC_USER_MICROSOFT,
                user_type_auth.PUBLIC_USER_YAHOO,
                user_type_auth.PUBLIC_USER_LINKEDIN,
                user_type_auth.PUBLIC_USER_GOOGLE,
                user_type_auth.PUBLIC_USER_NYC_ID,
                user_type_auth.ANONYMOUS_USER,
                name='auth_user_type'),
        primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey("requests.id"), primary_key=True)
    request_user_type = db.Column(
        db.Enum(user_type_request.REQUESTER,
                user_type_request.AGENCY,
                name='request_user_type'))
    permissions = db.Column(db.Integer)
    # Note: If an anonymous user creates a request, they will be listed in the UserRequests table, but will have the
    # same permissions as an anonymous user browsing a request since there is no method for authenticating that the
    # current anonymous user is in fact the requester.

    __table_args__ = (
        db.ForeignKeyConstraint(
            [user_guid, auth_user_type],
            [Users.guid, Users.auth_user_type]
        ),
    )

    def has_permission(self, permission):
        """
        Ex:
            has_permission(permission.ADD_NOTE)
        """
        return bool(self.permissions & permission)


class Metadatas(db.Model):
    """
    Parent class of response metadata classes (defined below this class).
    """
    __tablename__ = 'metadatas'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(
        'notes',
        'links',
        'files',
        'instructions',
        'extensions',
        'emails',
        name='metadata_type'
    ))
    __mapper_args__ = {'polymorphic_on': type}


class Notes(Metadatas):
    """
    Define the Notes class with the following columns and relationships:

    id - an integer that is the primary key of Notes
    content - a string that contains the content of a note
    """
    __tablename__ = 'notes'
    __mapper_args__ = {'polymorphic_identity': 'notes'}
    id = db.Column(db.Integer, db.ForeignKey(Metadatas.id), primary_key=True)
    content = db.Column(db.String(5000))


class Files(Metadatas):
    """
    Define the Files class with the following columns and relationships:

    id - an integer that is the primary key of Files
    name - a string containing the name of a file (name is the secured filename)
    mime_type - a string containing the mime_type of a file
    title - a string containing the title of a file (user defined)
    size - a string containing the size of a file
    """
    __tablename__ = 'files'
    __mapper_args__ = {'polymorphic_identity': 'files'}
    id = db.Column(db.Integer, db.ForeignKey('metadatas.id'), primary_key=True)
    name = db.Column(db.String)  # secured filename
    mime_type = db.Column(db.String)
    title = db.Column(db.String)
    size = db.Column(db.Integer)


class Links(Metadatas):
    """
    Define the Links class with the following columns and relationships:

    id - an integer that is the primary key of Links
    title - a string containing the title of a link
    url - a string containing the url link
    """
    __tablename__ = 'links'
    __mapper_args__ = {'polymorphic_identity': 'links'}
    id = db.Column(db.Integer, db.ForeignKey('metadatas.id'), primary_key=True)
    title = db.Column(db.String)
    url = db.Column(db.String)


class Instructions(Metadatas):
    """
    Define the Instructions class with the following columns and relationships:

    id - an integer that is the primary key of Instructions
    content - a string containing the content of an instruction
    """
    __tablename__ = 'instructions'
    __mapper_args__ = {'polymorphic_identity': 'instructions'}
    id = db.Column(db.Integer, db.ForeignKey('metadatas.id'), primary_key=True)
    content = db.Column(db.String)


class Extensions(Metadatas):
    """
    Define the Extensions class with the following columns and relationships:

    id - an integer that is the primary key of Extensions
    reason - a string containing the reason for an extension
    date - a datetime object containing the extended date of a request
    """
    __tablename__ = 'extensions'
    __mapper_args__ = {'polymorphic_identity': 'extensions'}
    id = db.Column(db.Integer, db.ForeignKey('metadatas.id'), primary_key=True)
    reason = db.Column(db.String)
    date = db.Column(db.DateTime)


class Emails(Metadatas):
    """
    Define the Emails class with the following columns and relationships:

    id - an integer that is the primary key of Emails
    to - a string containing who the the email is being sent to
    cc - a string containing who is cc'd in an email
    bcc -  a string containing who is bcc'd in an email
    subject - a string containing the subject of an email
    email_content - a string containing the content of an email
    linked_files - an array of strings containing the links to the files
    """
    __tablename__ = 'emails'
    __mapper_args__ = {'polymorphic_identity': 'emails'}
    id = db.Column(db.Integer, db.ForeignKey('metadatas.id'), primary_key=True)
    to = db.Column(db.String)
    cc = db.Column(db.String)
    bcc = db.Column(db.String)
    subject = db.Column(db.String(5000))
    email_content = db.Column(db.String)
    linked_files = db.Column(ARRAY(db.String))
