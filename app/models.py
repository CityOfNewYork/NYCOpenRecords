"""
Models for OpenRecords database
"""
import csv
from datetime import datetime
from operator import ior
from functools import reduce
from uuid import uuid4

from flask import current_app
from flask_login import UserMixin, AnonymousUserMixin
from sqlalchemy.dialects.postgresql import ARRAY, JSON

from app import db, es, calendar
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.constants import (
    ES_DATETIME_FORMAT,
    USER_ID_DELIMITER,
    DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS,
    permission,
    role_name,
    user_type_auth,
    user_type_request,
    request_status,
    response_type,
    determination_type,
    response_privacy,
    submission_methods,
)


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
                permission.NONE
            ),
            role_name.PUBLIC_REQUESTER: (
                permission.ADD_NOTE
            ),
            role_name.AGENCY_HELPER: (
                permission.ADD_NOTE |
                permission.ADD_FILE |
                permission.ADD_LINK |
                permission.ADD_OFFLINE_INSTRUCTIONS
            ),
            role_name.AGENCY_OFFICER: (
                permission.ACKNOWLEDGE |
                permission.DENY |
                permission.EXTEND |
                permission.CLOSE |
                permission.RE_OPEN |
                permission.ADD_NOTE |
                permission.ADD_FILE |
                permission.ADD_LINK |
                permission.ADD_OFFLINE_INSTRUCTIONS |
                permission.EDIT_NOTE |
                permission.EDIT_NOTE_PRIVACY |
                permission.EDIT_FILE |
                permission.EDIT_FILE_PRIVACY |
                permission.EDIT_LINK |
                permission.EDIT_LINK_PRIVACY |
                permission.EDIT_OFFLINE_INSTRUCTIONS |
                permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY |
                permission.EDIT_OFFLINE_INSTRUCTIONS |
                permission.EDIT_FILE_PRIVACY |
                permission.DELETE_NOTE |
                permission.DELETE_FILE |
                permission.DELETE_LINK |
                permission.DELETE_OFFLINE_INSTRUCTIONS |
                permission.EDIT_TITLE |
                permission.CHANGE_PRIVACY_TITLE |
                permission.EDIT_AGENCY_DESCRIPTION |
                permission.CHANGE_PRIVACY_AGENCY_DESCRIPTION |
                permission.EDIT_REQUESTER_INFO
            ),
            role_name.AGENCY_ADMIN: (
                permission.ACKNOWLEDGE |
                permission.DENY |
                permission.EXTEND |
                permission.CLOSE |
                permission.RE_OPEN |
                permission.ADD_NOTE |
                permission.ADD_FILE |
                permission.ADD_LINK |
                permission.ADD_OFFLINE_INSTRUCTIONS |
                permission.EDIT_NOTE |
                permission.EDIT_NOTE_PRIVACY |
                permission.EDIT_FILE |
                permission.EDIT_FILE_PRIVACY |
                permission.EDIT_LINK |
                permission.EDIT_LINK_PRIVACY |
                permission.EDIT_OFFLINE_INSTRUCTIONS |
                permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY |
                permission.EDIT_FILE_PRIVACY |
                permission.EDIT_TITLE |
                permission.DELETE_NOTE |
                permission.DELETE_FILE |
                permission.DELETE_LINK |
                permission.DELETE_OFFLINE_INSTRUCTIONS |
                permission.CHANGE_PRIVACY_TITLE |
                permission.EDIT_AGENCY_DESCRIPTION |
                permission.CHANGE_PRIVACY_AGENCY_DESCRIPTION |
                permission.ADD_USER_TO_REQUEST |
                permission.REMOVE_USER_FROM_REQUEST |
                permission.EDIT_USER_REQUEST_PERMISSIONS |
                permission.ADD_USER_TO_AGENCY |
                permission.REMOVE_USER_FROM_AGENCY |
                permission.CHANGE_USER_ADMIN_PRIVILEGE |
                permission.EDIT_REQUESTER_INFO
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
    administrators - an array of user id strings that identify default admins for an agencies requests
    """
    __tablename__ = 'agencies'
    ein = db.Column(db.String(4), primary_key=True)
    parent_ein = db.Column(db.String(3))
    categories = db.Column(ARRAY(db.String(256)))
    name = db.Column(db.String(256), nullable=False)
    next_request_number = db.Column(db.Integer(), db.Sequence('request_seq'))
    default_email = db.Column(db.String(254))
    appeals_email = db.Column(db.String(254))
    is_active = db.Column(db.Boolean(), default=False)

    administrators = db.relationship(
        'Users',
        primaryjoin="and_(Agencies.ein == Users.agency_ein, "
                    "Users.is_agency_active == True, "
                    "Users.is_agency_admin == True)"
    )
    standard_users = db.relationship(
        'Users',
        primaryjoin="and_(Agencies.ein == Users.agency_ein, "
                    "Users.is_agency_active == True, "
                    "Users.is_agency_admin == False)"
    )
    active_users = db.relationship(
        'Users',
        primaryjoin="and_(Agencies.ein == Users.agency_ein, "
                    "Users.is_agency_active == True)"
    )
    inactive_users = db.relationship(
        'Users',
        primaryjoin="and_(Agencies.ein == Users.agency_ein, "
                    "Users.is_agency_active == False)"
    )

    @classmethod
    def populate(cls):
        """
        Automatically populate the agencies table for the OpenRecords application.
        """
        with open(current_app.config['AGENCY_DATA'], 'r') as data:
            dictreader = csv.DictReader(data)

            for row in dictreader:
                agency = cls(
                    ein=row['ein'],
                    parent_ein=row['parent_ein'],
                    categories=row['categories'].split(','),
                    name=row['name'],
                    next_request_number=row['next_request_number'],
                    default_email=row['default_email'],
                    appeals_email=row['appeals_email'],
                    is_active=eval(row['is_active'])
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
    agency_ein - a foreign key that links to the primary key of the agency table
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
                user_type_auth.AGENCY_LDAP_USER,
                user_type_auth.PUBLIC_USER_FACEBOOK,
                user_type_auth.PUBLIC_USER_MICROSOFT,
                user_type_auth.PUBLIC_USER_YAHOO,
                user_type_auth.PUBLIC_USER_LINKEDIN,
                user_type_auth.PUBLIC_USER_GOOGLE,
                user_type_auth.PUBLIC_USER_NYC_ID,
                user_type_auth.ANONYMOUS_USER,
                name='auth_user_type'),
        primary_key=True)
    agency_ein = db.Column(db.String(4), db.ForeignKey('agencies.ein'))
    is_super = db.Column(db.Boolean, nullable=False, default=False)
    is_agency_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_agency_active = db.Column(db.Boolean, nullable=False, default=False)
    first_name = db.Column(db.String(32), nullable=False)
    middle_initial = db.Column(db.String(1))
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(254))
    email_validated = db.Column(db.Boolean(), nullable=False)
    terms_of_use_accepted = db.Column(db.Boolean)
    title = db.Column(db.String(64))
    organization = db.Column(db.String(128))  # Outside organization
    phone_number = db.Column(db.String(15))
    fax_number = db.Column(db.String(15))
    mailing_address = db.Column(JSON)  # TODO: define validation for minimum acceptable mailing address

    # Relationships
    user_requests = db.relationship("UserRequests", backref="user", lazy='dynamic')
    agency = db.relationship('Agencies', backref='users')

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
        return self.auth_user_type in user_type_auth.AGENCY_USER_TYPES

    @property
    def is_anonymous_requester(self):
        """
        Checks to see if the user is an anonymous requester

        NOTE: This is not the same as an anonymous user! This returns
        true if this user has been created for a specific request.

        :return: Boolean
        """
        return self.auth_user_type == user_type_auth.ANONYMOUS_USER

    @property
    def anonymous_request(self):
        """
        Returns the request this user is associated with
        if this user is an anonymous requester.
        """
        if self.is_anonymous_requester:
            return Requests.query.filter_by(id=self.user_requests.one().request_id).one()
        return None

    def get_id(self):  # FIXME: should not be getter
        return USER_ID_DELIMITER.join((self.guid, self.auth_user_type))

    def from_id(self, user_id):  # Might come in useful
        guid, auth_user_type = user_id.split(USER_ID_DELIMITER)
        return self.query.filter_by(guid=guid, auth_user_type=auth_user_type).one()

    @property
    def name(self):
        return ' '.join((self.first_name.title(), self.last_name.title()))

    def es_update(self):
        """
        Call es_update for any request where this user is the requester
        since the request es doc relies on the requester's name.
        """
        for request in self.requests:
            request.es_update()

    @property
    def val_for_events(self):
        """
        JSON to store in Events 'new_value' field.
        """
        return {
            "guid": self.guid,
            "auth_user_type": self.auth_user_type,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "organization": self.organization,
            "phone_number": self.phone_number,
            "fax_number": self.fax_number,
            "mailing_address": self.mailing_address,
            "email_validated": self.email_validated,
            "terms_of_use_accepted": self.terms_of_use_accepted,
        }

    @classmethod
    def populate(cls):
        with open(current_app.config['STAFF_DATA'], 'r') as data:
            dictreader = csv.DictReader(data)

            for row in dictreader:
                user = cls(
                    guid=str(uuid4()),
                    auth_user_type=user_type_auth.AGENCY_LDAP_USER if current_app.config['USE_LDAP'] else user_type_auth.AGENCY_USER,
                    agency_ein=row['agency_ein'],
                    is_super=eval(row['is_super']),
                    is_agency_admin=eval(row['is_agency_admin']),
                    is_agency_active=eval(row['is_agency_active']),
                    first_name=row['first_name'],
                    middle_initial=row['middle_initial'],
                    last_name=row['last_name'],
                    email=row['email'],
                    email_validated=eval(row['email_validated']),
                    terms_of_use_accepted=eval(row['terms_of_use_accepted']),
                    phone_number=row['phone_number'],
                    fax_number=row['fax_number']
                )
                db.session.add(user)
            db.session.commit()


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
    due_date - the date that is set five days after date_submitted,
        this has 2 meanings depending on the current status of a request:
            OPEN - the agency has to acknowledge the request by this date
            not OPEN - the request must be completed by this date
    submission - a Enum that selects from a list of submission methods
    status - an Enum that selects from a list of different statuses a request can have
    privacy - a JSON object that contains the boolean privacy options of a request's title and agency description
              (True = Private, False = Public)
    """
    __tablename__ = 'requests'
    id = db.Column(db.String(19), primary_key=True)
    agency_ein = db.Column(db.String(4), db.ForeignKey('agencies.ein'))
    category = db.Column(db.String, default='All', nullable=False)
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
    status = db.Column(
        db.Enum(request_status.OPEN,
                request_status.IN_PROGRESS,
                request_status.DUE_SOON,  # within the next 5 business days
                request_status.OVERDUE,
                request_status.CLOSED,
                name='status'),
        nullable=False
    )
    privacy = db.Column(JSON)
    agency_description = db.Column(db.String(5000))
    agency_description_release_date = db.Column(db.DateTime)

    user_requests = db.relationship('UserRequests', backref=db.backref('request', uselist=False), lazy='dynamic')
    agency = db.relationship('Agencies', backref='requests', uselist=False)
    responses = db.relationship('Responses', backref=db.backref('request', uselist=False), lazy='dynamic')
    requester = db.relationship(
        'Users',
        secondary='user_requests',  # expects table name
        primaryjoin=lambda: Requests.id == UserRequests.request_id,
        secondaryjoin="and_(Users.guid == UserRequests.user_guid, "
                      "Users.auth_user_type == UserRequests.auth_user_type,"
                      "UserRequests.request_user_type == '{}')".format(user_type_request.REQUESTER),
        backref="requests",
        viewonly=True,
        uselist=False
    )
    # any agency user associated with a request is considered an assigned user
    agency_users = db.relationship(
        'Users',
        secondary='user_requests',
        primaryjoin=lambda: Requests.id == UserRequests.request_id,
        secondaryjoin="and_(Users.guid == UserRequests.user_guid, "
                      "Users.auth_user_type == UserRequests.auth_user_type, "
                      "UserRequests.request_user_type == '{}')".format(user_type_request.AGENCY),
        viewonly=True
    )

    PRIVACY_DEFAULT = {'title': False, 'agency_description': True}

    def __init__(
            self,
            id,
            title,
            description,
            agency_ein,
            date_created,
            category=None,
            privacy=None,
            date_submitted=None,  # FIXME: are some of these really nullable?
            due_date=None,
            submission=None,
            status=request_status.OPEN
    ):
        self.id = id
        self.title = title
        self.description = description
        self.agency_ein = agency_ein
        self.date_created = date_created
        self.category = category
        self.privacy = privacy or self.PRIVACY_DEFAULT
        self.date_submitted = date_submitted
        self.due_date = due_date
        self.submission = submission
        self.status = status

    @property
    def val_for_events(self):
        """
        JSON to store in Events 'new_value' field.

        Values that will not change or that will always
        be the same on Request creation are not included.
        """
        return {
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat(),
        }

    @property
    def was_acknowledged(self):
        return self.responses.filter(
            Responses.type == response_type.DETERMINATION,
            Determinations.dtype == determination_type.ACKNOWLEDGMENT
        ).first() is not None

    def es_update(self):
        es.update(
            index=current_app.config["ELASTICSEARCH_INDEX"],
            doc_type='request',
            id=self.id,
            body={
                'doc': {
                    'title': self.title,
                    'description': self.description,
                    'agency_description': self.agency_description,
                    'title_private': self.privacy['title'],
                    'agency_description_private': self.privacy['agency_description'],
                    'date_due': self.due_date.strftime(ES_DATETIME_FORMAT),
                    'status': self.status,
                    'requester_name': self.requester.name,
                    'public_title': 'Private' if self.privacy['title'] else self.title
                }
            },
            # refresh='wait_for'
        )

    def es_create(self):
        """ Must be called AFTER UserRequest has been created. """
        es.create(
            index=current_app.config["ELASTICSEARCH_INDEX"],
            doc_type='request',
            id=self.id,
            body={
                'title': self.title,
                'description': self.description,
                'agency_description': self.agency_description,
                'agency_ein': self.agency_ein,
                'agency_name': self.agency.name,
                'title_private': self.privacy['title'],
                'agency_description_private': self.privacy['agency_description'],
                'date_created': self.date_created.strftime(ES_DATETIME_FORMAT),
                'date_submitted': self.date_submitted.strftime(ES_DATETIME_FORMAT),
                'date_due': self.due_date.strftime(ES_DATETIME_FORMAT),
                'submission': self.submission,
                'status': self.status,
                'requester_id': (self.requester.get_id()
                                 if not self.requester.is_anonymous_requester
                                 else ''),
                'requester_name': self.requester.name,
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
    previous_value - a string containing the old value of the event
    new_value - a string containing the new value of the event
    """
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('requests.id'))
    user_guid = db.Column(db.String(64))  # who did the action
    auth_user_type = db.Column(
        db.Enum(user_type_auth.AGENCY_USER,
                user_type_auth.AGENCY_LDAP_USER,
                user_type_auth.PUBLIC_USER_FACEBOOK,
                user_type_auth.PUBLIC_USER_MICROSOFT,
                user_type_auth.PUBLIC_USER_YAHOO,
                user_type_auth.PUBLIC_USER_LINKEDIN,
                user_type_auth.PUBLIC_USER_GOOGLE,
                user_type_auth.PUBLIC_USER_NYC_ID,
                user_type_auth.ANONYMOUS_USER,
                name='auth_user_type'))
    response_id = db.Column(db.Integer, db.ForeignKey('responses.id'))
    type = db.Column(db.String(30))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    previous_value = db.Column(JSON)
    new_value = db.Column(JSON)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [user_guid, auth_user_type],
            [Users.guid, Users.auth_user_type]
        ),
    )

    def __init__(self,
                 request_id,
                 user_guid,
                 auth_user_type,
                 type_,
                 previous_value=None,
                 new_value=None,
                 response_id=None,
                 timestamp=None):
        self.request_id = request_id
        self.user_guid = user_guid
        self.auth_user_type = auth_user_type
        self.response_id = response_id
        self.type = type_
        self.previous_value = previous_value
        self.new_value = new_value
        self.timestamp = timestamp

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
    privacy = db.Column(db.Enum(
        response_privacy.PRIVATE,
        response_privacy.RELEASE_AND_PRIVATE,
        response_privacy.RELEASE_AND_PUBLIC,
        name="privacy"))
    date_modified = db.Column(db.DateTime)
    release_date = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False, nullable=False)
    is_editable = db.Column(db.Boolean, default=False, nullable=False)
    type = db.Column(db.Enum(
        response_type.NOTE,
        response_type.LINK,
        response_type.FILE,
        response_type.INSTRUCTIONS,
        response_type.DETERMINATION,
        response_type.EMAIL,
        name='type'
    ))
    __mapper_args__ = {'polymorphic_on': type}

    # TODO: overwrite filter to automatically check if deleted=False

    def __init__(self,
                 request_id,
                 privacy,
                 date_modified=None,
                 is_editable=False):
        self.request_id = request_id
        self.privacy = privacy
        self.date_modified = date_modified or datetime.utcnow()
        self.release_date = (calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS)
                             if privacy == response_privacy.RELEASE_AND_PUBLIC
                             else None)
        self.is_editable = is_editable

    # NOTE: If you can find a way to make this class work with abc,
    # you're welcome to make the necessary changes to the following method:
    @property
    def preview(self):
        """ Designated preview attribute value. """
        raise NotImplementedError

    @property
    def val_for_events(self):
        """ JSON to store in Events 'new_value' field. """
        val = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            }
        val.pop('id')
        val['privacy'] = self.privacy
        return val

    def __repr__(self):
        return '<Responses %r>' % self.id


class Reasons(db.Model):
    """
    Define the Reason class with the following columns and relationships:

    id - an integer that is the primary key of a Reasons
    type - an enum representing the type of determination this reason corresponds to
    agency_ein - a foreign key that links to the a agency's primary key
        if null, this reason applies to all agencies
    content - a string describing the reason

    Reason are based off the Law Department's responses.

    """
    __tablename__ = 'reasons'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(
        determination_type.CLOSING,
        determination_type.DENIAL,
        name="reason_type"
    ), nullable=False)
    agency_ein = db.Column(db.String(4), db.ForeignKey('agencies.ein'))
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)

    @classmethod
    def populate(cls):
        with open(current_app.config['REASON_DATA'], 'r') as data:
            dictreader = csv.DictReader(data)

            for row in dictreader:
                reason = cls(
                    type=row['type'],
                    title=row['title'],
                    content=row['content']
                )
                db.session.add(reason)
            db.session.commit()


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
                user_type_auth.AGENCY_LDAP_USER,
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
    permissions = db.Column(db.BigInteger)
    # Note: If an anonymous user creates a request, they will be listed in the UserRequests table, but will have the
    # same permissions as an anonymous user browsing a request since there is no method for authenticating that the
    # current anonymous user is in fact the requester.

    __table_args__ = (
        db.ForeignKeyConstraint(
            [user_guid, auth_user_type],
            [Users.guid, Users.auth_user_type]
        ),
    )

    @property
    def val_for_events(self):
        """
        JSON to store in Events 'new_value' field.
        """
        return {
            "user_guid": self.user_guid,
            "auth_user_type": self.auth_user_type,
            "request_user_type": self.request_user_type,
            "permissions": self.permissions
        }

    def has_permission(self, perm):
        """
        Ex:
            has_permission(permission.ADD_NOTE)
        """
        return bool(self.permissions & perm)

    def add_permissions(self, permissions):
        """
        :param permissions: list of permissions from app.constants.permissions
        """
        self.permissions |= reduce(ior, permissions)
        db.session.commit()

    def remove_permissions(self, permissions):
        """
        :param permissions: list of permissions from app.constants.permissions
        """
        self.permissions &= ~reduce(ior, permissions)
        db.session.commit()

    def set_permissions(self, permissions):
        """
        :param permissions: list of permissions from app.constants.permissions
                            or a permissions bitmask
        """
        if isinstance(permissions, list):
            self.permissions = reduce(ior, permissions)
        else:
            self.permissions = permissions
        db.session.commit()

    def get_permissions(self):
        return [i for i, p in enumerate(permission.ALL) if bool(self.permissions & p.value)]


class ResponseTokens(db.Model):
    """
    Define the ResponseTokens class with the following columns and relationships:

    id - an integer that is the primary key of ResponseTokens
    token - a string consisting of a randomly-generated, unique token
    response_id - a foreign key that links to a response's primary key
    expiration_date - a datetime object containing the date at which this token becomes invalid
    """
    __tablename__ = 'response_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False)
    expiration_date = db.Column(db.DateTime)

    response = db.relationship("Responses", backref=db.backref("token", uselist=False))

    def __init__(self,
                 response_id,
                 expiration_date=None):
        self.token = self.generate_token()
        self.response_id = response_id
        self.expiration_date = expiration_date or calendar.addbusdays(
            datetime.utcnow(), DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS)

    @staticmethod
    def generate_token():
        return uuid4().hex


class Notes(Responses):
    """
    Define the Notes class with the following columns and relationships:

    id - an integer that is the primary key of Notes
    content - a string that contains the content of a note
    """
    __tablename__ = response_type.NOTE
    __mapper_args__ = {'polymorphic_identity': response_type.NOTE}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    content = db.Column(db.String(5000))
    # is_editable = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,
                 request_id,
                 privacy,
                 content,
                 date_modified=None,
                 is_editable=False):
        super(Notes, self).__init__(request_id,
                                    privacy,
                                    date_modified,
                                    is_editable)
        self.content = content

    @property
    def preview(self):
        return self.content


class Files(Responses):
    """
    Define the Files class with the following columns and relationships:

    id - an integer that is the primary key of Files
    name - a string containing the name of a file (name is the secured filename)
    mime_type - a string containing the mime_type of a file
    title - a string containing the title of a file (user defined)
    size - a string containing the size of a file
    hash - a string containing the sha1 hash of a file
    """
    __tablename__ = response_type.FILE
    __mapper_args__ = {'polymorphic_identity': response_type.FILE}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    title = db.Column(db.String)
    name = db.Column(db.String)
    mime_type = db.Column(db.String)
    size = db.Column(db.Integer)
    hash = db.Column(db.String)
    # is_editable = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,
                 request_id,
                 privacy,
                 title,
                 name,
                 mime_type,
                 size,
                 hash_,
                 date_modified=None,
                 is_editable=False):
        super(Files, self).__init__(request_id,
                                    privacy,
                                    date_modified,
                                    is_editable)
        self.name = name
        self.mime_type = mime_type
        self.title = title
        self.size = size
        self.hash = hash_

    @property
    def preview(self):
        return self.title


class Links(Responses):
    """
    Define the Links class with the following columns and relationships:

    id - an integer that is the primary key of Links
    title - a string containing the title of a link
    url - a string containing the url link
    """
    __tablename__ = response_type.LINK
    __mapper_args__ = {'polymorphic_identity': response_type.LINK}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    title = db.Column(db.String)
    url = db.Column(db.String)
    # is_editable = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,
                 request_id,
                 privacy,
                 title,
                 url,
                 date_modified=None,
                 is_editable=False):
        super(Links, self).__init__(request_id,
                                    privacy,
                                    date_modified,
                                    is_editable)
        self.title = title
        self.url = url

    @property
    def preview(self):
        return self.title


class Instructions(Responses):
    """
    Define the Instructions class with the following columns and relationships:

    id - an integer that is the primary key of Instructions
    content - a string containing the content of an instruction
    """
    __tablename__ = response_type.INSTRUCTIONS
    __mapper_args__ = {'polymorphic_identity': response_type.INSTRUCTIONS}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    content = db.Column(db.String)
    # is_editable = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,
                 request_id,
                 privacy,
                 content,
                 date_modified=None,
                 is_editable=False):
        super(Instructions, self).__init__(request_id,
                                           privacy,
                                           date_modified,
                                           is_editable)
        self.content = content

    @property
    def preview(self):
        return self.content


class Determinations(Responses):
    """
    Define the Determinations class with the following columns and relationships:

    id - an integer that is the primary key of Determinations
    dtype - a string (enum) containing the type of a determination
    reason - a string containing the reason for a determination
    date - a datetime object containing an appropriate date for a determination

    ext_type       | date significance                | reason significance
    ---------------|----------------------------------|------------------------------------------
    denial         | NA                               | why the request was denied
    acknowledgment | estimated date of completion     | why the date was chosen / additional info
    extension      | new estimated date of completion | why the request extended
    closing        | NA                               | why the request closed
    reopening      | new estimated date of completion | NA

    """
    __tablename__ = response_type.DETERMINATION
    __mapper_args__ = {'polymorphic_identity': response_type.DETERMINATION}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    dtype = db.Column(db.Enum(
        determination_type.DENIAL,
        determination_type.ACKNOWLEDGMENT,
        determination_type.EXTENSION,
        determination_type.CLOSING,
        determination_type.REOPENING,
        name="determination_type"
    ), nullable=False)
    reason = db.Column(db.String)  # nullable only for acknowledge and re-opening
    date = db.Column(db.DateTime)  # nullable only for denial, closing
    # is_editable = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,
                 request_id,
                 privacy,  # TODO: always RELEASE_AND_PUBLIC?
                 dtype,
                 reason,
                 date=None,
                 date_modified=None,
                 is_editable=False):
        super(Determinations, self).__init__(request_id,
                                             privacy,
                                             date_modified,
                                             is_editable)
        self.dtype = dtype

        if dtype not in (determination_type.ACKNOWLEDGMENT,
                         determination_type.REOPENING):
            assert reason is not None
        self.reason = reason

        if dtype not in (determination_type.DENIAL,
                         determination_type.CLOSING):
            assert date is not None
        self.date = date

    @property
    def preview(self):
        return self.reason

    @property
    def val_for_events(self):
        val = {
            'reason': self.reason
        }
        if self.dtype in (determination_type.ACKNOWLEDGMENT,
                          determination_type.EXTENSION,
                          determination_type.REOPENING):
            val['date'] = self.date.isoformat()
        return val


class Emails(Responses):
    """
    Define the Emails class with the following columns and relationships:

    id - an integer that is the primary key of Emails
    to - a string containing who the the email is being sent to
    cc - a string containing who is cc'd in an email
    bcc -  a string containing who is bcc'd in an email
    subject - a string containing the subject of an email
    email_content - a string containing the content of an email
    """
    __tablename__ = response_type.EMAIL
    __mapper_args__ = {'polymorphic_identity': response_type.EMAIL}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    to = db.Column(db.String)
    cc = db.Column(db.String)
    bcc = db.Column(db.String)
    subject = db.Column(db.String(5000))
    body = db.Column(db.String)
    # is_editable = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,
                 request_id,
                 privacy,
                 to,
                 cc,
                 bcc,
                 subject,
                 body,
                 date_modified=None,
                 is_editable=False):
        super(Emails, self).__init__(request_id,
                                     privacy,
                                     date_modified,
                                     is_editable)
        self.to = to
        self.cc = cc
        self.bcc = bcc
        self.subject = subject
        self.body = body

    @property
    def preview(self):
        return self.subject

    @property
    def val_for_events(self):
        return {
            'privacy': self.privacy,
            'body': self.body,
        }
