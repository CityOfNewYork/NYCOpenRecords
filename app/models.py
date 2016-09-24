"""
Models for open records database
"""

import csv
from datetime import datetime

from flask_login import UserMixin, AnonymousUserMixin
from flask_login import current_user
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import JSON


from app import app, db
from app.constants import PUBLIC_USER, AGENCY_USER


class Permission:
    """
    Define the permission codes for certain actions:

    DUPLICATE_REQUEST: Duplicate Request (New Request based on same criteria)
    VIEW_REQUEST_STATUS_PUBLIC: View detailed request status (Open, In Progress, Closed)
    VIEW_REQUEST_STATUS_ALL: View detailed request status (Open, In Progress, Due Soon, Overdue, Closed)
    VIEW_REQUEST_INFO_PUBLIC: View all public request information
    VIEW_REQUEST_INFO_ALL: View all request information
    ADD_NOTE: Add Note (Agency Only) or (Agency Only & Requester Only) or (Agency Only, Requester / Agency)
    UPLOAD_DOCUMENTS: Upload Documents (Agency Only & Requester Only) or (Agency Only / Private) or
                        (Agency Only / Private, Agency / Requester, All Users)
    VIEW_DOCUMENTS_IMMEDIATELY: View Documents Immediately - Public or 'Released and Private'
    VIEW_REQUESTS_HELPER: View requests where they are assigned
    VIEW_REQUESTS_AGENCY: View all requests for their agency
    VIEW_REQUESTS_ALL: View all requests for all agencies
    EXTEND_REQUESTS: Extend Request
    CLOSE_REQUESTS: Close Request (Denial/Fulfill)
    ADD_HELPERS: Add Helper (Helper permissions must be specified on a per request basis)
    REMOVE_HELPERS: Remove Helper
    ACKNOWLEDGE: Acknowledge
    CHANGE_REQUEST_POC: Change Request POC
    ADMINISTER: All permissions
    """
    DUPLICATE_REQUEST = 0x00001
    VIEW_REQUEST_STATUS_PUBLIC = 0x00002
    VIEW_REQUEST_STATUS_ALL = 0x00004
    VIEW_REQUEST_INFO_PUBLIC = 0x00008
    VIEW_REQUEST_INFO_ALL = 0x00010
    ADD_NOTE = 0x00020
    UPLOAD_DOCUMENTS = 0x00040
    VIEW_DOCUMENTS_IMMEDIATELY = 0x00080
    VIEW_REQUESTS_HELPER = 0x00100
    VIEW_REQUESTS_AGENCY = 0x00200
    VIEW_REQUESTS_ALL = 0x00400
    EXTEND_REQUESTS = 0x00800
    CLOSE_REQUESTS = 0x01000
    ADD_HELPERS = 0x02000
    REMOVE_HELPERS = 0x04000
    ACKNOWLEDGE = 0x08000
    CHANGE_REQUEST_POC = 0x10000
    ADMINISTER = 0x20000


class Role(db.Model):
    """
    Define the Role class with the following columns and relationships:

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

    @staticmethod
    def insert_roles():
        """
        Insert permissions for each role: Anonymous User, Public User - Non Requester, Public User - Requester,
        Agency Helper, Agency FOIL Officer, Agency Administrator.
        """
        roles = {
            'Anonymous User': (Permission.DUPLICATE_REQUEST | Permission.VIEW_REQUEST_STATUS_PUBLIC |
                               Permission.VIEW_REQUEST_INFO_PUBLIC, True),
            'Public User - Non Requester': (Permission.ADD_NOTE | Permission.DUPLICATE_REQUEST |
                                            Permission.VIEW_REQUEST_STATUS_PUBLIC | Permission.VIEW_REQUEST_INFO_PUBLIC,
                                            False),
            'Public User - Requester': (Permission.ADD_NOTE | Permission.UPLOAD_DOCUMENTS |
                                        Permission.VIEW_DOCUMENTS_IMMEDIATELY | Permission.VIEW_REQUEST_INFO_ALL |
                                        Permission.VIEW_REQUEST_STATUS_PUBLIC, False),
            'Agency Helper': (Permission.ADD_NOTE | Permission.UPLOAD_DOCUMENTS | Permission.VIEW_REQUESTS_HELPER |
                              Permission.VIEW_REQUEST_INFO_ALL | Permission.VIEW_REQUEST_STATUS_ALL, False),
            'Agency FOIL Officer': (Permission.ADD_NOTE | Permission.UPLOAD_DOCUMENTS | Permission.EXTEND_REQUESTS |
                                    Permission.CLOSE_REQUESTS | Permission.ADD_HELPERS | Permission.REMOVE_HELPERS |
                                    Permission.ACKNOWLEDGE | Permission.VIEW_REQUESTS_AGENCY |
                                    Permission.VIEW_REQUEST_INFO_ALL | Permission.VIEW_REQUEST_STATUS_ALL, False),
            'Agency Administrator': (Permission.ADD_NOTE | Permission.UPLOAD_DOCUMENTS | Permission.EXTEND_REQUESTS |
                                     Permission.CLOSE_REQUESTS | Permission.ADD_HELPERS | Permission.REMOVE_HELPERS |
                                     Permission.ACKNOWLEDGE | Permission.CHANGE_REQUEST_POC |
                                     Permission.VIEW_REQUESTS_ALL | Permission.VIEW_REQUEST_INFO_ALL |
                                     Permission.VIEW_REQUEST_STATUS_ALL, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class Agency(db.Model):
    """
    Define the Agency class with the following columns and relationships:

    ein - the primary key of the agency table, 3 digit integer that is unique for each agency
    category - a string containing the category of the agency (ex: business/education)
    name - a string containing the name of the agency
    next_request_number - a sequence containing the next number for the request starting at 1, each agency has its own
                          request number sequence
    default_email - a string containing the default email of the agency regarding general inquiries about requests
    appeal_email - a string containing the appeal email for users regarding the agency closing or denying requests
    """

    __tablename__ = 'agency'
    ein = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(256))
    name = db.Column(db.String(256), nullable=False)
    next_request_number = db.Column(db.Integer(), db.Sequence('request_seq'))
    default_email = db.Column(db.String(254))
    appeals_email = db.Column(db.String(254))

    @staticmethod
    def insert_agencies():
        """
        Automatically populate the agency table for the OpenRecords application.
        """
        data = open(app.config['AGENCY_DATA'], 'r')
        dictreader = csv.DictReader(data)

        for row in dictreader:
            agency = Agency(
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
        return '<Agency %r>' % self.name


class UserRequest(db.Model):
    """
    Define the UserRequest class with the following columns and relationships:
    A UserRequest is a many to many relationship between users who are related to a certain request
    user_guid and request_id are combined to create a composite primary key

    user_guid = a foreign key that links to the primary key of the User table
    request_id = a foreign key that links to the primary key of the Request table
    """

    __tablename__ = 'user_request'
    user_guid = db.Column(db.String(1000), db.ForeignKey("user.guid"), primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey("request.id"), primary_key=True)
    permission = db.Column(db.Integer)


class User(UserMixin, db.Model):
    """
    Define the User class with the following columns and relationships:

    guid - a string that contains the unique guid of a agency user
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
    __tablename__ = 'user'
    guid = db.Column(db.String(64), primary_key=True, unique=True)  # guid + user type
    user_type = db.Column(db.String(64), primary_key=True)
    agency = db.Column(db.Integer, db.ForeignKey('agency.ein'))
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
        super(User, self).__init__(**kwargs)

    def __repr__(self):
        return '<User {}:{}>'.format(self.guid, self.user_type)


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


class Request(db.Model):
    """
    Define the Request class with the following columns and relationships:

    id - a string containing the requst id, of the form: FOIL - year 4 digits - EIN 3 digits - 5 digits for request number
    agency - a foreign key that links that the primary key of the agency the request was assigned to
    title - a string containing a short description of the request
    description - a string containing a full description of what is needed from the request
    date_created - the actual creation time of the request
    date_submitted - a date that rolls forward to the next business day based on date_created
    due_date - the date that is set five days after date_submitted, the agency has to acknowledge the request by the due date
    submission - a Enum that selects from a list of submission methods
    current_status - a Enum that selects from a list of different statuses a request can have
    visibility - a JSON object that contains the visbility settings of a request
    """

    __tablename__ = 'request'
    id = db.Column(db.String(19), primary_key=True)
    agency = db.Column(db.Integer, db.ForeignKey('agency.ein'))
    title = db.Column(db.String(90))
    description = db.Column(db.String(5000))
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    date_submitted = db.Column(db.DateTime)  # used to calculate due date, rounded off to next business day
    due_date = db.Column(db.DateTime)
    # submission = db.Column(db.Enum('fill in types here', name='submission_type'))
    submission = db.Column(
        db.String(30))  # direct input/mail/fax/email/phone/311/text method of answering request default is direct input
    current_status = db.Column(db.Enum('Open', 'In Progress', 'Due Soon', 'Overdue', 'Closed', 'Re-Opened',
                                       name='statuses'))  # due soon is within the next "5" business days
    visibility = db.Column(JSON)

    def __init__(
            self,
            id,
            title,
            description,
            agency,
            date_created,
            date_submitted=None,
            due_date=None,
            submission=None,
            current_status=None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.agency = agency
        self.date_created = date_created
        self.date_submitted = date_submitted
        self.due_date = due_date
        self.submission = submission
        self.current_status = current_status

    def __repr__(self):
        return '<Request %r>' % self.id


class Event(db.Model):
    """
    Define the Event class with the following columns and relationships:
    Events are any type of action that happened to a request after it was submitted

    id - an integer that is the primary key of an Event
    request_id - a foreign key that links to a request's primary key
    user_id - a foreign key that links to the user_id of the person who performed the event
    response_id - a foreign key that links to the primary key of a response
    type - a string containing the type of event that occurred
    timestamp - a datetime that keeps track of what time an event was performed
    previous_response_value - a string containing the old response value
    new_response_value - a string containing the new response value
    """

    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('request.id'))
    user_id = db.Column(db.String(64))  # who did the action
    user_type = db.Column(db.String(64))
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'))
    type = db.Column(db.String(30))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    previous_response_value = db.Column(db.String)
    new_response_value = db.Column(db.String)

    __table_args__ = (ForeignKeyConstraint([user_id, user_type],
                                           [User.guid, User.user_type]),
                      {})

    def __repr__(self):
        return '<Event %r>' % self.id


class Response(db.Model):
    """
    Define the Response class with the following columns and relationships:

    id - an integer that is the primary key of a Response
    request_id - a foreign key that links to the primary key of a request
    type - a string containing the type of response that was given for a request
    date_modified - a datetime object that keeps track of when a request was changed
    content - a JSON object that contains the content for all the possible responses a request can have
    privacy - a string containing the privacy option for a response
    """

    __tablename__ = 'response'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('request.id'))
    type = db.Column(db.String(30))
    date_modified = db.Column(db.DateTime)
    content = db.Column(JSON)
    privacy = db.Column(db.String(7))

    def __repr__(self):
        return '<Response %r>' % self.id


class Reason(db.Model):
    """
    Define the Reason class with the following columns and relationships:

    id - an integer that is the primary key of a Reason
    agency - a foreign key that links to the a agency's primary key which is the EIN number
    deny_reason - a string containing the message that will be shown when a request is denied
    """

    __tablename__ = 'reason'
    id = db.Column(db.Integer, primary_key=True)
    agency = db.Column(db.Integer, db.ForeignKey('agency.ein'), nullable=True)
    deny_reason = db.Column(db.String)  # reasons for denying a request based off law dept's responses
