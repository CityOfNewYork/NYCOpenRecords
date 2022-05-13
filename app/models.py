"""
Models for OpenRecords database
"""
import csv
import json
from datetime import datetime
from urllib.parse import urljoin
from uuid import uuid4

from elasticsearch.helpers import bulk
from flask import current_app, session
from flask_login import UserMixin, AnonymousUserMixin, current_user
from functools import reduce
from operator import ior
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import column_property
from sqlalchemy.orm.exc import MultipleResultsFound
from warnings import warn

from app import db, es, calendar, sentry
from app.constants import (
    ES_DATETIME_FORMAT,
    permission,
    role_name,
    user_type_request,
    request_status,
    response_type,
    determination_type,
    response_privacy,
    submission_methods,
    event_type,
)
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.constants.schemas import AGENCIES_SCHEMA
from app.lib.json_schema import validate_schema
from app.lib.utils import (
    eval_request_bool,
    DuplicateFileException,
    InvalidDeterminationException,
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

    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permissions = db.Column(db.BigInteger)

    @classmethod
    def populate(cls):
        """
        Insert permissions for each role.
        """
        roles = {
            role_name.ANONYMOUS: (permission.NONE),
            role_name.PUBLIC_REQUESTER: (permission.ADD_NOTE),
            role_name.AGENCY_HELPER: (
                permission.ADD_NOTE
                | permission.ADD_FILE
                | permission.ADD_LINK
                | permission.ADD_OFFLINE_INSTRUCTIONS
            ),
            role_name.AGENCY_OFFICER: (
                permission.ACKNOWLEDGE
                | permission.DENY
                | permission.EXTEND
                | permission.CLOSE
                | permission.RE_OPEN
                | permission.ADD_NOTE
                | permission.ADD_FILE
                | permission.ADD_LINK
                | permission.ADD_OFFLINE_INSTRUCTIONS
                | permission.GENERATE_LETTER
                | permission.EDIT_NOTE
                | permission.EDIT_NOTE_PRIVACY
                | permission.EDIT_FILE
                | permission.EDIT_FILE_PRIVACY
                | permission.EDIT_LINK
                | permission.EDIT_LINK_PRIVACY
                | permission.EDIT_OFFLINE_INSTRUCTIONS
                | permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY
                | permission.EDIT_OFFLINE_INSTRUCTIONS
                | permission.EDIT_FILE_PRIVACY
                | permission.DELETE_NOTE
                | permission.DELETE_FILE
                | permission.DELETE_LINK
                | permission.DELETE_OFFLINE_INSTRUCTIONS
                | permission.EDIT_TITLE
                | permission.CHANGE_PRIVACY_TITLE
                | permission.EDIT_AGENCY_REQUEST_SUMMARY
                | permission.CHANGE_PRIVACY_AGENCY_REQUEST_SUMMARY
                | permission.EDIT_REQUESTER_INFO
            ),
            role_name.AGENCY_ADMIN: (
                permission.ACKNOWLEDGE
                | permission.DENY
                | permission.EXTEND
                | permission.CLOSE
                | permission.RE_OPEN
                | permission.ADD_NOTE
                | permission.ADD_FILE
                | permission.ADD_LINK
                | permission.ADD_OFFLINE_INSTRUCTIONS
                | permission.GENERATE_LETTER
                | permission.EDIT_NOTE
                | permission.EDIT_NOTE_PRIVACY
                | permission.EDIT_FILE
                | permission.EDIT_FILE_PRIVACY
                | permission.EDIT_LINK
                | permission.EDIT_LINK_PRIVACY
                | permission.EDIT_OFFLINE_INSTRUCTIONS
                | permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY
                | permission.EDIT_FILE_PRIVACY
                | permission.EDIT_TITLE
                | permission.DELETE_NOTE
                | permission.DELETE_FILE
                | permission.DELETE_LINK
                | permission.DELETE_OFFLINE_INSTRUCTIONS
                | permission.CHANGE_PRIVACY_TITLE
                | permission.EDIT_AGENCY_REQUEST_SUMMARY
                | permission.CHANGE_PRIVACY_AGENCY_REQUEST_SUMMARY
                | permission.ADD_USER_TO_REQUEST
                | permission.REMOVE_USER_FROM_REQUEST
                | permission.EDIT_USER_REQUEST_PERMISSIONS
                | permission.ADD_USER_TO_AGENCY
                | permission.REMOVE_USER_FROM_AGENCY
                | permission.CHANGE_USER_ADMIN_PRIVILEGE
                | permission.EDIT_REQUESTER_INFO
            ),
        }

        for name, value in roles.items():
            role = Roles.query.filter_by(name=name).first()
            if role is None:
                role = cls(name=name)
            role.permissions = value
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return "<Roles %r>" % self.name


class Agencies(db.Model):
    """
    Define the Agencies class with the following columns and relationships:
    ein - the primary key of the agencies table, 3 digit integer that is unique for each agency
    parent_ein - the ein that corresponds to the agency to which the ein belongs. This is used for agencies such as the
                 Mayor's Office, who have a number of smaller agencies that handle their own FOIL offices.
    categories - an array of strings containing the category of the agency (ex: business/education)
    name - a string containing the name of the agency
    next_request_number - a sequence containing the next number for the request starting at 1, each agency has its own
                          request number sequence
    default_email - a string containing the default email of the agency regarding general inquiries about requests
    appeal_email - a string containing the appeal email for users regarding the agency closing or denying requests
    is_active - a boolean field denoting whether an agency is currently using the OpenRecords system to serve FOIL
                requests. Defaults to False.
    monitors_sub_agencies - a boolean field that denotes whether administrators for this agency should be able to edit
                            requests for sub-agencies. Defaults to False.

    administrators - an array of user id strings that identify default admins for an agencies requests
    standard_users - an array of user id strings that identify agency users (non-admins) for an agencies requests
    active_users - an array of user id strings that identify agency users (admin and non-admin) that can login to
                   OpenRecords.
    inactive_users - an array of user id strings that identify agency users (admin and non-admin) that cannot login to
                     OpenRecords

    """

    __tablename__ = "agencies"
    ein = db.Column(db.String(4), primary_key=True)
    parent_ein = db.Column(db.String(3))
    categories = db.Column(ARRAY(db.String(256)))
    _name = db.Column(db.String(256), nullable=False, name="name")
    acronym = db.Column(db.String(64), nullable=True)
    _next_request_number = db.Column(
        db.Integer(), db.Sequence("request_seq"), name="next_request_number"
    )
    default_email = db.Column(db.String(254))
    appeals_email = db.Column(db.String(254))
    is_active = db.Column(db.Boolean(), default=False)
    agency_features = db.Column(JSONB)
    # TODO: Method to insert updates to the agency_features column
    # TODO: Use validation on agency_features column

    administrators = db.relationship(
        "Users",
        secondary="agency_users",
        primaryjoin="and_(Agencies.ein == AgencyUsers.agency_ein, "
        "AgencyUsers.is_agency_active == True, "
        "AgencyUsers.is_agency_admin == True)",
        secondaryjoin="AgencyUsers.user_guid == Users.guid",
    )
    standard_users = db.relationship(
        "Users",
        secondary="agency_users",
        primaryjoin="and_(Agencies.ein == AgencyUsers.agency_ein, "
        "AgencyUsers.is_agency_active == True, "
        "AgencyUsers.is_agency_admin == False)",
        secondaryjoin="AgencyUsers.user_guid == Users.guid",
    )
    active_users = db.relationship(
        "Users",
        secondary="agency_users",
        primaryjoin="and_(Agencies.ein == AgencyUsers.agency_ein, "
        "AgencyUsers.is_agency_active == True)",
        secondaryjoin="AgencyUsers.user_guid == Users.guid",
    )
    inactive_users = db.relationship(
        "Users",
        secondary="agency_users",
        primaryjoin="and_(Agencies.ein == AgencyUsers.agency_ein, "
        "AgencyUsers.is_agency_active == False)",
        secondaryjoin="AgencyUsers.user_guid == Users.guid",
    )

    @property
    def formatted_parent_ein(self):
        """
        Return the correctly formatted EIN for a parent agency.

        Parent EINs are ALWAYS preceded by a 0, since City of New York EINs are always 3 characters.
        :return: String
        """
        return "0{}".format(self.parent_ein)

    @property
    def parent(self):
        return Agencies.query.filter_by(ein=self.formatted_parent_ein).one_or_none()

    @property
    def next_request_number(self):
        from app.lib.db_utils import update_object

        num = self._next_request_number
        update_object(
            {"_next_request_number": self._next_request_number + 1},
            Agencies,
            self.formatted_parent_ein,
        )
        return num

    @next_request_number.setter
    def next_request_number(self, value):
        self._next_request_number = value

    @property
    def name(self):
        return (
            "{name} ({acronym})".format(name=self._name, acronym=self.acronym)
            if self.acronym
            else "{name}".format(name=self._name)
        )

    @name.setter
    def name(self, value):
        self._name = value

    @classmethod
    def populate(cls, json_name=None):
        """
        Automatically populate the agencies table for the OpenRecords application.
        """
        filename = json_name or current_app.config["AGENCY_DATA"]
        with open(filename, "r") as data:
            data = json.load(data)

            if not validate_schema(data, AGENCIES_SCHEMA):
                warn(
                    "Invalid JSON Data. Not importing any agencies.",
                    category=UserWarning,
                )
                return False

            for agency in data["agencies"]:
                if Agencies.query.filter_by(ein=agency["ein"]).first() is not None:
                    warn(
                        "Duplicate EIN ({ein}); Row not imported".format(
                            ein=agency["ein"]
                        ),
                        category=UserWarning,
                    )
                    continue
                a = cls(
                    ein=agency["ein"],
                    parent_ein=agency["parent_ein"],
                    categories=agency["categories"],
                    name=agency["name"],
                    acronym=agency.get("acronym", None),
                    next_request_number=agency["next_request_number"],
                    default_email=agency["default_email"],
                    appeals_email=agency["appeals_email"],
                    is_active=agency["is_active"],
                    agency_features=agency["agency_features"],
                )
                db.session.add(a)
            db.session.commit()

    def __repr__(self):
        return "<Agencies %r>" % self.name


class Users(UserMixin, db.Model):
    """
    Define the Users class with the following columns and relationships:

    guid - a string that contains the unique guid of users
    is_nyc_employee - a boolean value that determines if the user is a NYC Employee
    has_nyc_account - a boolean value that determines if the user has a NYC account
    active - a boolean value that determines if the user can login to NYC.ID
    agency_ein - a foreign key that links to the primary key of the agency table
    email - a string containing the user's email
    notification_email - a string containing the user's email for notifications
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

    __tablename__ = "users"
    guid = db.Column(db.String(64), unique=True, primary_key=True)
    is_nyc_employee = db.Column(db.Boolean, default=False)
    has_nyc_account = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=False)
    is_anonymous_requester = db.Column(db.Boolean)
    is_super = db.Column(db.Boolean, nullable=False, default=False)
    first_name = db.Column(db.String(32), nullable=False)
    middle_initial = db.Column(db.String(1))
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(254))
    notification_email = db.Column(db.String(254), nullable=True, default=None)
    email_validated = db.Column(db.Boolean(), nullable=False)
    terms_of_use_accepted = db.Column(db.Boolean)
    title = db.Column(db.String(64))
    organization = db.Column(db.String(128))  # Outside organization
    phone_number = db.Column(db.String(25))
    fax_number = db.Column(db.String(25))
    _mailing_address = db.Column(
        JSONB, name="mailing_address"
    )  # TODO: define validation for minimum acceptable mailing address
    session_id = db.Column(db.String(254), nullable=True, default=None)
    signature = db.Column(db.String(), nullable=True, default=None)
    fullname = column_property(first_name + " " + last_name)

    # Relationships
    user_requests = db.relationship("UserRequests", backref="user", lazy="dynamic")
    agencies = db.relationship(
        "Agencies",
        secondary="agency_users",
        primaryjoin="AgencyUsers.user_guid == Users.guid",
        secondaryjoin="and_(AgencyUsers.agency_ein == Agencies.ein, "
        "AgencyUsers.is_agency_active == True)",
        lazy="dynamic",
    )
    agency_users = db.relationship("AgencyUsers", backref="user", lazy="dynamic")
    mfa = db.relationship("MFA", backref="user", lazy="dynamic")

    @property
    def is_authenticated(self):
        """
        Verifies the access token currently stored in the user's session
        by invoking the OAuth User Web Service and checking the response.
        """
        if current_app.config["USE_LDAP"]:
            return True
        if current_app.config["USE_SAML"]:
            if session.get("samlUserdata", None):
                return True
        if current_app.config["USE_LOCAL_AUTH"]:
            return True
        return False

    @property
    def is_active(self):
        return self.email_validated

    @property
    def is_public(self):
        """
        Checks to see if the current user is a public user as defined below:
        :return: Boolean
        """
        return not self.is_nyc_employee and not self.is_anonymous_requester

    @property
    def is_agency(self):
        """
        Check to see if the current user is an agency user.

        :return: Boolean
        """
        return self.is_nyc_employee

    @property
    def get_agencies(self):
        """
        Returns a list of the agency ein's the user belongs to.
        """
        agencies = AgencyUsers.query.filter_by(user_guid=self.guid).all()
        return [agency.agency_ein for agency in agencies]

    @property
    def default_agency_ein(self):
        """
        Return the Users default agency ein.
        :return: String
        """
        agency = (
            AgencyUsers.query.join(Users)
            .filter(
                AgencyUsers.is_primary_agency == True,
                AgencyUsers.user_guid == self.guid,
            )
            .one_or_none()
        )
        if agency is not None:
            return agency.agency_ein
        return None

    @property
    def find_admin_agency_ein(self):
        """
        Find the ein of the agency the user is an admin for.
        If the user is admin for multiple agencies it will return the first one.
        :return: Agency ein
        """
        for agency in AgencyUsers.query.filter_by(user_guid=self.guid):
            if self.is_agency_admin(agency.agency_ein):
                return agency.agency_ein

    @property
    def default_agency(self):
        """
        Return the Users default Agencies object.
        :return: Agencies
        """
        return Agencies.query.filter_by(ein=self.default_agency_ein).one()

    @property
    def has_nyc_id_profile(self):
        """
        Checks to see if the current user has authenticated with
        NYC.ID, which means they have an NYC.ID Profile.

        :return: Boolean
        """
        return self.has_nyc_account or self.is_nyc_employee

    @property
    def anonymous_request(self):
        """
        Returns the request this user is associated with
        if this user is an anonymous requester.
        """
        if self.is_anonymous_requester:
            return Requests.query.filter_by(
                id=self.user_requests.one().request_id
            ).one()
        return None

    @property
    def has_agency_admin(self):
        """
        Determine if a user is an admin for at least one agency.
        :return: Boolean
        """
        for agency in self.agency_users.all():
            if agency.is_agency_admin:
                return True
        return False

    @property
    def has_agency_active(self):
        """
        Determine if a user is active for at least one agency.
        :return: Boolean
        """
        for agency in self.agency_users.all():
            if agency.is_agency_active:
                return True
        return False

    def is_agency_admin(self, ein=None):
        """
        Determine if a user is an admin for the specified agency.
        :param ein: Agency EIN (4 Character String)
        :return: Boolean
        """
        if ein is None:
            ein = self.default_agency_ein
        for agency in self.agency_users.all():
            if agency.agency_ein == ein:
                return agency.is_agency_admin
        return False

    def is_agency_active(self, ein=None):
        """
        Determine if a user is active for the specified agency.
        :param ein: Agency EIN (4 Character String)
        :return: Boolean
        """
        if ein is None:
            ein = self.default_agency_ein
        for agency in self.agency_users.all():
            if agency.agency_ein == ein:
                return agency.is_agency_active
        return False

    def agencies_for_forms(self):
        agencies = self.agencies.with_entities(Agencies.ein, Agencies._name).all()
        # Convert the results of with_entities back to tuple format so that agencies can be processed
        agencies = [tuple(agency) for agency in agencies]
        agencies.insert(
            0,
            agencies.pop(
                agencies.index((self.default_agency.ein, self.default_agency._name))
            ),
        )
        return agencies

    @property
    def name(self):
        return " ".join((self.first_name.title(), self.last_name.title()))

    @property
    def mailing_address(self):
        return self._mailing_address if self._mailing_address is not None else {}

    @mailing_address.setter
    def mailing_address(self, mailing_address):
        self._mailing_address = mailing_address

    @property
    def formatted_point_of_contact_number(self):
        if self.phone_number:
            formatted_phone_number = self.phone_number
            formatted_phone_number = formatted_phone_number.strip("(")
            formatted_phone_number = formatted_phone_number.replace(") ", "-")
            return formatted_phone_number

    def get_id(self):
        return self.guid

    @property
    def has_mfa(self):
        """
        Determine if a user has MFA set up.
        :return: Boolean
        """
        mfa = MFA.query.filter_by(user_guid=self.guid,
                                  is_valid=True).first()
        if mfa is not None:
            return True
        return False

    def es_update(self):
        """
        Call es_update for any request where this user is the requester
        since the request es doc relies on the requester's name.
        """
        if current_app.config["ELASTICSEARCH_ENABLED"]:
            requests = [request.id for request in self.requests]
            actions = [
                {
                    "_op_type": "update",
                    "_id": request_id,
                    "doc": {"requester_id": self.guid, "requester_name": self.name},
                }
                for request_id in requests
            ]

            bulk(
                es,
                actions,
                index=current_app.config["ELASTICSEARCH_INDEX"],
                chunk_size=current_app.config["ELASTICSEARCH_CHUNK_SIZE"],
            )

    @property
    def val_for_events(self):
        """
        JSON to store in Events 'new_value' field.
        """
        return {
            "guid": self.guid,
            "email": self.email,
            "notification_email": self.notification_email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "organization": self.organization,
            "phone_number": self.phone_number,
            "fax_number": self.fax_number,
            "mailing_address": self.mailing_address,
            "email_validated": self.email_validated,
            "terms_of_use_accepted": self.terms_of_use_accepted,
            "active": self.active,
            "has_nyc_account": self.has_nyc_account,
            "is_nyc_employee": self.is_nyc_employee,
            "is_anonymous_requester": self.is_anonymous_requester,
        }

    @classmethod
    def populate(cls, csv_name=None):
        filename = csv_name or current_app.config["STAFF_DATA"]
        with open(filename, "r") as data:
            dictreader = csv.DictReader(data)
            for row in dictreader:
                if Users.query.filter_by(email=row["email"]).first() is None:
                    user = cls(
                        guid=str(uuid4()),
                        is_super=eval(row["is_super"]),
                        first_name=row["first_name"],
                        middle_initial=row["middle_initial"],
                        last_name=row["last_name"],
                        email=row["email"],
                        email_validated=eval(row["email_validated"]),
                        terms_of_use_accepted=eval(row["terms_of_use_accepted"]),
                        phone_number=row["phone_number"],
                        fax_number=row["fax_number"],
                    )
                    db.session.add(user)
                    db.session.commit()

                    agency_eins = row["agencies"].split("|")
                    for agency in agency_eins:
                        ein, is_active, is_admin, is_primary_agency = agency.split("#")
                        agency_user = AgencyUsers(
                            user_guid=user.guid,
                            agency_ein=ein,
                            is_agency_active=eval_request_bool(is_active),
                            is_agency_admin=eval_request_bool(is_admin),
                            is_primary_agency=eval_request_bool(is_primary_agency),
                        )
                        db.session.add(agency_user)
                    if agency_eins:
                        user.is_nyc_employee = True
                    db.session.add(user)
            db.session.commit()

    def __init__(self, **kwargs):
        super(Users, self).__init__(**kwargs)

    def __repr__(self):
        return "<Users {}>".format(self.get_id())


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

    def __repr__(self):
        return "<Anonymous User>"


class AgencyUsers(db.Model):
    """
    Define the AgencyUsers class with the following columns and relationships:

    user_guid - a string that contains the unique guid of users
    agency_ein - a foreign key that links that the primary key of the agency the request was assigned to
    user_guid and agency_ein are combined to create a composite primary key
    is_agency_active - a boolean value that allows the user to login as a user for the agency identified by agency_ein
    is_agency_admin - a boolean value that allows the user to administer settings for the agency identified by
        agency_ein
    primary_agency - a boolean value that determines whether the agency identified by agency_ein is the users default
        agency
    """

    __tablename__ = "agency_users"
    user_guid = db.Column(db.String(64), db.ForeignKey("users.guid"), primary_key=True)
    agency_ein = db.Column(
        db.String(4), db.ForeignKey("agencies.ein"), primary_key=True
    )
    is_agency_active = db.Column(db.Boolean, default=False, nullable=False)
    is_agency_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_primary_agency = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.ForeignKeyConstraint([user_guid], [Users.guid], onupdate="CASCADE"),
    )


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
    privacy - a JSON object that contains the boolean privacy options of a request's title and agency request summary
              (True = Private, False = Public)
    agency_request_summary - a string that contains an additional description of the request created by the agency
    agency_request_summary_release_date - a datetime of when the agency_request_summary will be made public
    custom_metadata - a JSON that contains the metadata from an agency's custom request forms
    """

    __tablename__ = "requests"
    id = db.Column(db.String(19), primary_key=True)
    agency_ein = db.Column(db.String(4), db.ForeignKey("agencies.ein"))
    category = db.Column(
        db.String, default="All", nullable=False
    )  # FIXME: should be nullable, 'All' shouldn't be used
    title = db.Column(db.String(90))
    description = db.Column(db.String(5000))
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    date_submitted = db.Column(
        db.DateTime
    )  # used to calculate due date, rounded off to next business day
    date_closed = db.Column(db.DateTime, default=None, nullable=True)
    due_date = db.Column(db.DateTime)
    submission = db.Column(
        db.Enum(
            submission_methods.DIRECT_INPUT,
            submission_methods.FAX,
            submission_methods.PHONE,
            submission_methods.EMAIL,
            submission_methods.MAIL,
            submission_methods.IN_PERSON,
            submission_methods.THREE_ONE_ONE,
            name="submission",
        )
    )
    status = db.Column(
        db.Enum(
            request_status.OPEN,
            request_status.IN_PROGRESS,
            request_status.DUE_SOON,  # within the next 5 business days
            request_status.OVERDUE,
            request_status.CLOSED,
            name="status",
        ),
        nullable=False,
    )
    privacy = db.Column(JSONB)
    agency_request_summary = db.Column(db.String(5000))
    agency_request_summary_release_date = db.Column(db.DateTime)
    custom_metadata = db.Column(JSONB)

    user_requests = db.relationship(
        "UserRequests", backref=db.backref("request", uselist=False), lazy="dynamic"
    )
    agency = db.relationship("Agencies", backref="requests", uselist=False)
    responses = db.relationship(
        "Responses", backref=db.backref("request", uselist=False), lazy="dynamic"
    )
    requester = db.relationship(
        "Users",
        secondary="user_requests",  # expects table name
        primaryjoin=lambda: Requests.id == UserRequests.request_id,
        secondaryjoin="and_(Users.guid == UserRequests.user_guid, "
        "UserRequests.request_user_type == '{}')".format(user_type_request.REQUESTER),
        backref="requests",
        viewonly=True,
        uselist=False,
    )
    # any agency user associated with a request is considered an assigned user
    agency_users = db.relationship(
        "Users",
        secondary="user_requests",
        primaryjoin=lambda: Requests.id == UserRequests.request_id,
        secondaryjoin="and_(Users.guid == UserRequests.user_guid, "
        "UserRequests.request_user_type == '{}')".format(user_type_request.AGENCY),
        viewonly=True,
    )

    PRIVACY_DEFAULT = {"title": False, "agency_request_summary": True}

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
        status=request_status.OPEN,
        custom_metadata=None,
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
        self.custom_metadata = custom_metadata

    @property
    def val_for_events(self):
        """
        JSON to store in Events 'new_value' field.

        Values that will not change or that will always
        be the same on Request creation are not included.
        """
        return {
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat(),
        }

    @property
    def was_acknowledged(self):
        if (
            self.responses.join(Determinations)
            .filter(Determinations.dtype == determination_type.ACKNOWLEDGMENT)
            .one_or_none()
            is not None
        ):
            return True
        return False

    @property
    def was_reopened(self):
        return (
            self.responses.join(Determinations)
            .filter(Determinations.dtype == determination_type.REOPENING)
            .first()
            is not None
        )

    @property
    def last_date_closed(self):
        if self.status == request_status.CLOSED:
            return (
                self.responses.join(Determinations)
                .filter(
                    Determinations.dtype.in_(
                        [determination_type.CLOSING, determination_type.DENIAL]
                    )
                )
                .order_by(desc(Determinations.date_modified))
                .limit(1)
                .one()
                .date_modified
            )
        return None

    @property
    def days_until_due(self):
        return calendar.busdaycount(
            datetime.utcnow(), self.due_date.replace(hour=23, minute=59, second=59)
        )

    @property
    def show_title(self) -> bool:
        """Determine whether the title should be displayed on the front-end.
        The title may be displayed in the following circumstances:
            - The currently logged in user is in the requests assigned agency users OR
            - The current User is the requester OR
            - The title is not private AND
                - The request was acknowledged OR
                - The request was denied OR
                - The request is overdue for an acknowledgment
        Returns:
            bool: True if the title should be shown, False otherwise.
        """
        return (
            current_user in self.agency_users
            or current_user == self.requester
            or (
                not self.privacy["title"]
                and (
                    self.was_acknowledged
                    or self.status == request_status.CLOSED
                    or self.days_until_due < 0
                )
            )
        )

    @property
    def url(self):
        """
        Flask.request-independent url.

        Since we cannot use SERVER_NAME in config (and, by extension, 'url_for'),
        BASE_URL and VIEW_REQUEST_ENDPOINT will have to do.
        """
        return urljoin(
            current_app.config["BASE_URL"],
            "{view_request_endpoint}/{request_id}".format(
                view_request_endpoint=current_app.config["VIEW_REQUEST_ENDPOINT"],
                request_id=self.id,
            ),
        )

    @property
    def agency_request_summary_released(self):
        """
        Determine whether the agency_request_summary has been made public and has passed its release date
        """
        return (
            self.status == request_status.CLOSED
            and not self.privacy["agency_request_summary"]
            and self.agency_request_summary
            and self.agency_request_summary_release_date is not None
            and self.agency_request_summary_release_date < datetime.utcnow()
        )

    def es_update(self):
        if current_app.config["ELASTICSEARCH_ENABLED"]:
            if self.agency.is_active:
                es.update(
                    index=current_app.config["ELASTICSEARCH_INDEX"],
                    id=self.id,
                    body={
                        "doc": {
                            "title": self.title,
                            "description": self.description,
                            "agency_request_summary": self.agency_request_summary,
                            "assigned_users": [
                                user.get_id() for user in self.agency_users
                            ],
                            "title_private": self.privacy["title"],
                            "agency_request_summary_private": not self.agency_request_summary_released,
                            "date_due": self.due_date.strftime(ES_DATETIME_FORMAT),
                            "date_closed": self.date_closed.strftime(ES_DATETIME_FORMAT)
                            if self.date_closed is not None
                            else [],
                            "status": self.status,
                            "requester_name": self.requester.name,
                            "requester_id": (
                                self.requester.get_id()
                                if not self.requester.is_anonymous_requester
                                else ""
                            ),
                            "public_title": "Private"
                            if self.privacy["title"]
                            else self.title,
                        }
                    },
                    # refresh='wait_for'
                )

    def es_create(self):
        """ Must be called AFTER UserRequest has been created. """
        if current_app.config["ELASTICSEARCH_ENABLED"]:
            es.create(
                index=current_app.config["ELASTICSEARCH_INDEX"],
                id=self.id,
                body={
                    "title": self.title,
                    "description": self.description,
                    "agency_request_summary": self.agency_request_summary,
                    "agency_ein": self.agency_ein,
                    "agency_name": self.agency.name,
                    "assigned_users": [user.get_id() for user in self.agency_users],
                    "agency_acronym": self.agency.acronym,
                    "title_private": self.privacy["title"],
                    "agency_request_summary_private": not self.agency_request_summary_released,
                    "date_created": self.date_created.strftime(ES_DATETIME_FORMAT),
                    "date_submitted": self.date_submitted.strftime(ES_DATETIME_FORMAT),
                    "date_received": self.date_created.strftime(ES_DATETIME_FORMAT)
                    if self.date_created < self.date_submitted
                    else self.date_submitted.strftime(ES_DATETIME_FORMAT),
                    "date_due": self.due_date.strftime(ES_DATETIME_FORMAT),
                    "submission": self.submission,
                    "status": self.status,
                    "requester_id": (
                        self.requester.get_id()
                        if not self.requester.is_anonymous_requester
                        else ""
                    ),
                    "requester_name": self.requester.name,
                    "public_title": "Private" if self.privacy["title"] else self.title,
                    "request_type": [metadata["form_name"] for metadata in self.custom_metadata.values()],
                },
            )

    def es_delete(self):
        """ Delete a document from the elastic search index """
        if current_app.config["ELASTICSEARCH_ENABLED"]:
            es.delete(
                index=current_app.config["ELASTICSEARCH_INDEX"],
                id=self.id,
            )

    def __repr__(self):
        return "<Requests %r>" % self.id


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

    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey("requests.id"))
    user_guid = db.Column(db.String(64))
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"))
    type = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    previous_value = db.Column(JSONB)
    new_value = db.Column(JSONB)

    __table_args__ = (
        db.ForeignKeyConstraint([user_guid], [Users.guid], onupdate="CASCADE"),
    )

    response = db.relationship("Responses", backref="events")
    request = db.relationship("Requests", backref="events")
    user = db.relationship(
        "Users", primaryjoin="Events.user_guid == Users.guid", backref="events"
    )

    def __init__(
        self,
        request_id,
        user_guid,
        type_,
        previous_value=None,
        new_value=None,
        response_id=None,
        timestamp=None,
    ):
        self.request_id = request_id
        self.user_guid = user_guid
        self.response_id = response_id
        self.type = type_
        self.previous_value = previous_value
        self.new_value = new_value
        self.timestamp = timestamp or datetime.utcnow()

    def __repr__(self):
        return "<Events %r>" % self.id

    @property
    def affected_user(self):
        if self.new_value is not None and "user_guid" in self.new_value:
            return Users.query.filter_by(guid=self.new_value["user_guid"]).one()

    class RowContent(object):
        def __init__(
            self, event, verb, string, affected_user=None, no_user_string=None
        ):
            """
            :param verb: action describing event
            :param string: format()-ready string where first field is verb and
                           last field is affected_user, if applicable.
            :param affected_user: user affected by this event
            :param no_user_string: format()-ready string where there is no event user
            """
            self.event = event
            self.string = string
            self.verb = self._format_verb(verb)
            self.affected_user = affected_user
            self.no_user_string = no_user_string

        def __str__(self):
            format_args = [self.verb]
            if self.affected_user is not None:
                format_args += [self.affected_user.name]
            if self.no_user_string is not None and self.event.user is None:
                string = self.no_user_string
            else:
                string = " ".join((self.event.user.name, self.string))
            return string.format(*format_args)

        @staticmethod
        def _format_verb(verb):
            return "<strong>{}</strong>".format(verb)

    @property
    def history_row_content(self):
        """
        Returns html safe string for use in the rows of the history section,
        or None if this event is not intended for display purposes.
        """
        if self.type == event_type.REQ_STATUS_CHANGED:
            return "This request's status was <strong>changed</strong> to:<br>{}".format(
                self.new_value["status"]
            )

        valid_types = {
            event_type.USER_ADDED: self.RowContent(
                self, "added", "{} user: {}.", self.affected_user, "User {}: {}."
            ),
            event_type.USER_REMOVED: self.RowContent(
                self, "removed", "{} user: {}.", self.affected_user
            ),
            event_type.USER_PERM_CHANGED: self.RowContent(
                self, "changed", "{} permssions for user: {}.", self.affected_user
            ),
            event_type.REQUESTER_INFO_EDITED: self.RowContent(
                self, "changed", "{} the requester's information."
            ),
            event_type.REQ_CREATED: self.RowContent(
                self, "created", "{} this request."
            ),
            event_type.AGENCY_REQ_CREATED: self.RowContent(
                self,
                "created",
                "{} this request on behalf of {}.",
                self.request.requester,
            ),
            event_type.REQ_ACKNOWLEDGED: self.RowContent(
                self, "acknowledged", "{} this request."
            ),
            event_type.REQ_EXTENDED: self.RowContent(
                self, "extended", "{} this request."
            ),
            event_type.REQ_CLOSED: self.RowContent(self, "closed", "{} this request."),
            event_type.REQ_DENIED: self.RowContent(self, "denied", "{} this request."),
            event_type.REQ_REOPENED: self.RowContent(
                self, "re-opened", "{} this request."
            ),
            event_type.REQ_TITLE_EDITED: self.RowContent(
                self, "changed", "{} the title."
            ),
            event_type.REQ_AGENCY_REQ_SUM_EDITED: self.RowContent(
                self, "changed", "{} the agency request summary."
            ),
            event_type.REQ_TITLE_PRIVACY_EDITED: self.RowContent(
                self, "changed", "{} the title privacy."
            ),
            event_type.REQ_AGENCY_REQ_SUM_PRIVACY_EDITED: self.RowContent(
                self, "changed", "{} the agency request summary privacy."
            ),
            event_type.FILE_ADDED: self.RowContent(
                self, "added", "{} a file response."
            ),
            event_type.FILE_EDITED: self.RowContent(
                self, "changed", "{} a file response."
            ),
            event_type.FILE_REMOVED: self.RowContent(
                self, "deleted", "{} a file response."
            ),
            event_type.LINK_ADDED: self.RowContent(
                self, "added", "{} a link response."
            ),
            event_type.LINK_EDITED: self.RowContent(
                self, "changed", "{} a link response."
            ),
            event_type.LINK_REMOVED: self.RowContent(
                self, "deleted", "{} a link response."
            ),
            event_type.INSTRUCTIONS_ADDED: self.RowContent(
                self, "added", "{} an offline instructions response."
            ),
            event_type.INSTRUCTIONS_EDITED: self.RowContent(
                self, "changed", "{} an offline instructions response."
            ),
            event_type.INSTRUCTIONS_REMOVED: self.RowContent(
                self, "deleted", "{} an offline instructions response."
            ),
            event_type.NOTE_ADDED: self.RowContent(
                self, "added", "{} a note response."
            ),
            event_type.NOTE_EDITED: self.RowContent(
                self, "changed", "{} a note response."
            ),
            event_type.NOTE_REMOVED: self.RowContent(
                self, "deleted", "{} a note response."
            ),
            event_type.ENVELOPE_CREATED: self.RowContent(
                self, "created", "{} an envelope."
            ),
            event_type.RESPONSE_LETTER_CREATED: self.RowContent(
                self, "added", "{} a letter."
            ),
        }

        if self.type in valid_types:
            return str(valid_types[self.type])


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

    __tablename__ = "responses"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey("requests.id"))
    privacy = db.Column(
        db.Enum(
            response_privacy.PRIVATE,
            response_privacy.RELEASE_AND_PRIVATE,
            response_privacy.RELEASE_AND_PUBLIC,
            name="privacy",
        )
    )
    date_modified = db.Column(db.DateTime)
    release_date = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False, nullable=False)
    is_editable = db.Column(db.Boolean, default=False, nullable=False)
    type = db.Column(
        db.Enum(
            response_type.NOTE,
            response_type.LINK,
            response_type.FILE,
            response_type.INSTRUCTIONS,
            response_type.DETERMINATION,
            response_type.EMAIL,
            response_type.LETTER,
            response_type.ENVELOPE,
            name="type",
        )
    )

    __mapper_args__ = {"polymorphic_on": type}

    # TODO: overwrite filter to automatically check if deleted=False

    def __init__(self, request_id, privacy, date_modified=None, is_editable=False):
        self.request_id = request_id
        self.privacy = privacy
        self.date_modified = date_modified or datetime.utcnow()
        self.release_date = (
            calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS)
            if privacy == response_privacy.RELEASE_AND_PUBLIC
            else None
        )
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
        val = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        val.pop("id")
        val["privacy"] = self.privacy
        return val

    @property
    def is_public(self):
        return (
            self.privacy == response_privacy.RELEASE_AND_PUBLIC
            and self.release_date is not None
            and datetime.utcnow() > self.release_date
        )

    @property
    def creator(self):
        return (
            Events.query.filter(
                Events.response_id == self.id,
                Events.type.in_(event_type.RESPONSE_ADDED_TYPES),
            )
            .one()
            .user
        )

    @property
    def communication_method_type(self):
        """
        Determine the communication method for a response.

        :return: response_type.LETTER or response_type.EMAIL
        :rtype: str
        """
        communication_methods = CommunicationMethods.query.filter_by(
            response_id=self.id
        ).all()
        return (
            response_type.LETTER
            if response_type.LETTER in [cm.method_type for cm in communication_methods]
            else response_type.EMAIL
        )

    @property
    def event_timestamp(self):
        """
        This function runs a query on the Events table to get all associated event rows for a response and returns
        the newest timestamp of the newest event which will be displayed on the frontend.
        :return: timestamp of the newest event row associated with a response
        """
        timestamps = (
            Events.query.filter_by(response_id=self.id)
            .order_by(desc(Events.timestamp))
            .all()
        )
        if timestamps:
            return timestamps[0].timestamp
        return self.date_modified

    def make_public(self):
        self.privacy = response_privacy.RELEASE_AND_PUBLIC
        self.release_date = calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS)
        db.session.commit()

    def __repr__(self):
        return "<Responses %r>" % self.id


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

    __tablename__ = "reasons"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(
        db.Enum(
            determination_type.CLOSING,
            determination_type.DENIAL,
            determination_type.REOPENING,
            name="reason_type",
        ),
        nullable=False,
    )
    agency_ein = db.Column(db.String(4), db.ForeignKey("agencies.ein"))
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)
    has_appeals_language = db.Column(db.Boolean, default=True)

    @classmethod
    def populate(cls):
        with open(current_app.config["REASON_DATA"], "r") as data:
            dictreader = csv.DictReader(data)

            for row in dictreader:
                agency_ein = row["agency_ein"] if row["agency_ein"] else None
                reason = cls(
                    type=row["type"],
                    title=row["title"],
                    content=row["content"],
                    has_appeals_language=eval_request_bool(row["has_appeals_language"]),
                    agency_ein=agency_ein,
                )
                if not Reasons.query.filter_by(
                    title=row["title"], content=row["content"], agency_ein=agency_ein
                ).first():
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
    point_of_contact = a boolean to determine the point of contact of a request
    """

    __tablename__ = "user_requests"
    user_guid = db.Column(db.String(64), primary_key=True)
    request_id = db.Column(
        db.String(19), db.ForeignKey("requests.id"), primary_key=True
    )
    request_user_type = db.Column(
        db.Enum(
            user_type_request.REQUESTER,
            user_type_request.AGENCY,
            name="request_user_type",
        )
    )
    permissions = db.Column(db.BigInteger)
    point_of_contact = db.Column(db.Boolean, default=False)
    # Note: If an anonymous user creates a request, they will be listed in the UserRequests table, but will have the
    # same permissions as an anonymous user browsing a request since there is no method for authenticating that the
    # current anonymous user is in fact the requester.

    __table_args__ = (
        db.ForeignKeyConstraint([user_guid], [Users.guid], onupdate="CASCADE"),
    )

    @property
    def val_for_events(self):
        """
        JSON to store in Events 'new_value' field.
        """
        return {
            "user_guid": self.user_guid,
            "request_user_type": self.request_user_type,
            "permissions": self.permissions,
            "point_of_contact": self.point_of_contact,
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

    def get_permission_choice_indices(self):
        return [
            i for i, p in enumerate(permission.ALL) if bool(self.permissions & p.value)
        ]


class ResponseTokens(db.Model):
    """
    Define the ResponseTokens class with the following columns and relationships:

    id - an integer that is the primary key of ResponseTokens
    token - a string consisting of a randomly-generated, unique token
    response_id - a foreign key that links to a response's primary key
    expiration_date - a datetime object containing the date at which this token becomes invalid
    """

    __tablename__ = "response_tokens"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False)

    response = db.relationship("Responses", backref=db.backref("token", uselist=False))

    def __init__(self, response_id):
        self.token = self.generate_token()
        self.response_id = response_id

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
    __mapper_args__ = {"polymorphic_identity": response_type.NOTE}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    content = db.Column(db.String)

    def __init__(
        self, request_id, privacy, content, date_modified=None, is_editable=False
    ):
        super(Notes, self).__init__(request_id, privacy, date_modified, is_editable)
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
    __mapper_args__ = {"polymorphic_identity": response_type.FILE}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    title = db.Column(db.String(250))
    name = db.Column(db.String)
    mime_type = db.Column(db.String)
    size = db.Column(db.Integer)
    hash = db.Column(db.String)

    def __init__(
        self,
        request_id,
        privacy,
        title,
        name,
        mime_type,
        size,
        hash_,
        date_modified=None,
        is_editable=False,
    ):
        try:
            file_exists = Files.query.filter_by(request_id=request_id, hash=hash_).all()
            for file in file_exists:
                if not file.deleted:
                    raise DuplicateFileException(file_name=name, request_id=request_id)
        except DuplicateFileException:
            sentry.captureException()
            raise DuplicateFileException(file_name=name, request_id=request_id)
        except MultipleResultsFound:
            sentry.captureException()
            raise DuplicateFileException(file_name=name, request_id=request_id)

        super(Files, self).__init__(request_id, privacy, date_modified, is_editable)
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
    __mapper_args__ = {"polymorphic_identity": response_type.LINK}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    title = db.Column(db.String)
    url = db.Column(db.String)

    def __init__(
        self, request_id, privacy, title, url, date_modified=None, is_editable=False
    ):
        super(Links, self).__init__(request_id, privacy, date_modified, is_editable)
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
    __mapper_args__ = {"polymorphic_identity": response_type.INSTRUCTIONS}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    content = db.Column(db.String)

    def __init__(
        self, request_id, privacy, content, date_modified=None, is_editable=False
    ):
        super(Instructions, self).__init__(
            request_id, privacy, date_modified, is_editable
        )
        self.content = content

    @property
    def preview(self):
        return self.content


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
    __mapper_args__ = {"polymorphic_identity": response_type.EMAIL}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    to = db.Column(db.String)
    cc = db.Column(db.String)
    bcc = db.Column(db.String)
    subject = db.Column(db.String(5000))
    body = db.Column(db.String)

    def __init__(
        self,
        request_id,
        privacy,
        to,
        cc,
        bcc,
        subject,
        body,
        date_modified=None,
        is_editable=False,
    ):
        super(Emails, self).__init__(request_id, privacy, date_modified, is_editable)
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
        return {"privacy": self.privacy, "body": self.body}


class Envelopes(Responses):
    """
    Define an Envelopes class with the following columns and relationships:

    id - an integer that is the primary key of Envelopes (FK to Responses)
    latex - the latex used to generate the envelope PDF
    """

    __tablename__ = response_type.ENVELOPE
    __mapper_args__ = {"polymorphic_identity": response_type.ENVELOPE}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    latex = db.Column(db.String)

    def __init__(
        self, request_id, privacy, latex, date_modified=None, is_editable=False
    ):
        super(Envelopes, self).__init__(request_id, privacy, date_modified, is_editable)
        self.latex = latex

    @property
    def preview(self):
        return "Envelope for {request_id}".format(request_id=self.request_id)


class EnvelopeTemplates(db.Model):
    """
    Define the EnvelopeTemplates class with the following columns and relationships:

    id - an integer that is the primary key of a EnvelopeTemplates
    agency_ein - a foreign key that links to the a agency's primary key
        if null, this envelope template applies to all agencies
    title - a short descriptor for the envelope template
    template_name - the name of the template to be loaded from the filesystem
    """

    __tablename__ = "envelope_templates"
    id = db.Column(db.Integer, primary_key=True)
    agency_ein = db.Column(db.String(4), db.ForeignKey("agencies.ein"))
    title = db.Column(db.String, nullable=False)
    template_name = db.Column(db.String, nullable=False)

    @classmethod
    def populate(cls, csv_name=None):
        filename = csv_name or current_app.config["ENVELOPE_TEMPLATES_DATA"]
        print(filename)
        with open(filename, "r") as data:
            dictreader = csv.DictReader(data)
            for row in dictreader:
                if (
                    EnvelopeTemplates.query.filter_by(
                        agency_ein=row["agency_ein"],
                        title=row["title"],
                        template_name=row["template_name"],
                    ).one_or_none()
                    is None
                ):
                    template = EnvelopeTemplates(
                        agency_ein=row["agency_ein"],
                        title=row["title"],
                        template_name=row["template_name"],
                    )
                    db.session.add(template)

            db.session.commit()


class Letters(Responses):
    """
    Define a Letters class with the following columns and relationships:

    id - an integer that is the primary key of Letters (FK to Responses)
    content - A string containing the content of a letter (HTML Formatted)
    """

    __tablename__ = response_type.LETTER
    __mapper_args__ = {"polymorphic_identity": response_type.LETTER}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.String)

    def __init__(
        self, request_id, privacy, title, content, date_modified=None, is_editable=False
    ):
        super(Letters, self).__init__(request_id, privacy, date_modified, is_editable)
        self.title = title
        self.content = content

    @property
    def preview(self):
        return self.title


class LetterTemplates(db.Model):
    """
    Define the Reason class with the following columns and relationships:

    id - an integer that is the primary key of a Reasons
    type - an enum representing the type of determination this reason corresponds to
    agency_ein - a foreign key that links to the a agency's primary key
        if null, this reason applies to all agencies
    content - a string describing the reason

    Reason are based off the Law Department's responses.

    """

    __tablename__ = "letter_templates"
    id = db.Column(db.Integer, primary_key=True)
    type_ = db.Column(
        db.Enum(
            determination_type.ACKNOWLEDGMENT,
            determination_type.EXTENSION,
            determination_type.CLOSING,
            determination_type.DENIAL,
            determination_type.REOPENING,
            response_type.LETTER,
            name="letter_type",
        ),
        nullable=False,
        name="type",
    )
    agency_ein = db.Column(db.String(4), db.ForeignKey("agencies.ein"))
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)

    @classmethod
    def populate(cls, csv_name=None):
        filename = csv_name or current_app.config["LETTER_TEMPLATES_DATA"]
        with open(filename, "r") as data:
            dictreader = csv.DictReader(data)
            for row in dictreader:
                if (
                    LetterTemplates.query.filter_by(
                        type_=row["type"],
                        agency_ein=row["agency_ein"],
                        title=row["title"],
                        content=row["content"],
                    ).one_or_none()
                    is None
                ):
                    template = LetterTemplates(
                        type_=row["type"],
                        agency_ein=row["agency_ein"],
                        title=row["title"],
                        content=row["content"],
                    )
                    db.session.add(template)

            db.session.commit()


class Determinations(Responses):
    """
    Define the Determinations class with the following columns and relationships:

    id - an integer that is the primary key of Determinations
    dtype - a string (enum) containing the type of a determination
    reason - a string containing the reason for a determination
    date - a datetime object containing an appropriate date for a determination

    ext_type       | date significance                | reason significance
    ---------------|----------------------------------|------------------------------------------
    denial         | N/A                              | why the request was denied
    acknowledgment | estimated date of completion     | why the date was chosen / additional info
    extension      | new estimated date of completion | why the request extended
    closing        | N/A                              | why the request closed
    reopening      | new estimated date of completion | N/A

    """

    __tablename__ = response_type.DETERMINATION
    __mapper_args__ = {"polymorphic_identity": response_type.DETERMINATION}
    id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    dtype = db.Column(
        db.Enum(
            determination_type.DENIAL,
            determination_type.ACKNOWLEDGMENT,
            determination_type.EXTENSION,
            determination_type.CLOSING,
            determination_type.REOPENING,
            name="determination_type",
        ),
        nullable=False,
    )
    reason = db.Column(db.String)  # nullable only for acknowledge and re-opening
    date = db.Column(db.DateTime)  # nullable only for denial, closing

    def __init__(
        self,
        request_id,
        privacy,  # TODO: always RELEASE_AND_PUBLIC?
        dtype,
        reason,
        date=None,
        date_modified=None,
        is_editable=False,
    ):
        super(Determinations, self).__init__(
            request_id, privacy, date_modified, is_editable
        )
        self.dtype = dtype

        if (
            dtype
            not in (determination_type.ACKNOWLEDGMENT, determination_type.REOPENING)
            and reason is None
        ):
            raise InvalidDeterminationException(
                request_id=request_id, dtype=dtype, missing_field="reason"
            )
        self.reason = reason

        if (
            dtype not in (determination_type.DENIAL, determination_type.CLOSING)
            and date is None
        ):
            raise InvalidDeterminationException(
                request_id=request_id, dtype=dtype, missing_field="date"
            )
        self.date = date

    @property
    def preview(self):
        return self.reason

    @property
    def val_for_events(self):
        val = {"reason": self.reason}
        if self.dtype in (
            determination_type.ACKNOWLEDGMENT,
            determination_type.EXTENSION,
            determination_type.REOPENING,
        ):
            val["due_date"] = self.date.isoformat()
        return val


class CommunicationMethods(db.Model):
    """
    A response can have another correlating response (letter or email). CommunicationMethods stores the response and
    its correlating response.
    Ex: An acknowledgment can have a letter and a email response.

    Define a CommunicationMethods class with the following columns and relationships:

    response_id - an integer that is a primary key of CommunicationMetholds (FK to Responses)
    method_id - an integer that is a primary key of CommunicationMethods (FK to Responses)
    method_type - enum ('letters', 'emails') method associated with the response
    """

    __tablename__ = "communication_methods"
    response_id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    method_id = db.Column(db.Integer, db.ForeignKey(Responses.id), primary_key=True)
    method_type = db.Column(
        db.Enum(
            response_type.LETTER, response_type.EMAIL, name="communication_method_type"
        ),
        nullable=True,
    )

    def __init__(self, response_id, method_id, method_type):
        self.response_id = response_id
        self.method_id = method_id
        self.method_type = method_type


class CustomRequestForms(db.Model):
    """
    Define the CustomRequestForms class with the following columns and relationships:

    id - an integer that is the primary key of CustomRequestForms
    agency_ein - a string that is a foreign key to the Agencies table
    form_name - a string that is the name of the custom form
    form_description - a string that prompts the user what the form is about and how to fill it out
    field_definitions - a JSON that contains the the name of the field as the key and type of field as the value
    repeatable - an integer the determines if that form is repeatable. 0 = not repeatable, 1 = can be added twice, etc.
    category - an integer to separate different types of custom forms for an agency
    minimum_required - an integer to dictates the minimum amount of fields required for a successful submission
    """

    __tablename__ = "custom_request_forms"
    id = db.Column(db.Integer, primary_key=True)
    agency_ein = db.Column(db.String(4), db.ForeignKey("agencies.ein"), nullable=False)
    form_name = db.Column(db.String, nullable=False)
    form_description = db.Column(db.String, nullable=False)
    field_definitions = db.Column(JSONB, nullable=False)
    repeatable = db.Column(db.Integer, nullable=False)
    category = db.Column(db.Integer, nullable=True)
    minimum_required = db.Column(db.Integer, nullable=True)

    @classmethod
    def populate(cls, json_name=None):
        """
        Automatically populate the custom_request_forms table for the OpenRecords application.
        """
        filename = json_name or current_app.config["CUSTOM_REQUEST_FORMS_DATA"]
        with open(filename, "r") as data:
            data = json.load(data)

            for form in data["custom_request_forms"]:
                if (
                    CustomRequestForms.query.filter_by(
                        agency_ein=form["agency_ein"], form_name=form["form_name"]
                    ).first()
                    is not None
                ):
                    warn(
                        "Duplicate custom_request_form ({}); Row not imported".format(
                            form["agency_ein"]
                        ),
                        category=UserWarning,
                    )
                    continue
                custom_request_form = cls(
                    agency_ein=form["agency_ein"],
                    form_name=form["form_name"],
                    form_description=form["form_description"],
                    field_definitions=form["field_definitions"],
                    repeatable=form["repeatable"],
                    category=form["category"],
                    minimum_required=form["minimum_required"],
                )
                db.session.add(custom_request_form)
            db.session.commit()


class MFA(db.Model):
    __tablename__ = "mfa"
    id = db.Column(db.Integer, primary_key=True)
    user_guid = db.Column(db.String(64), db.ForeignKey("users.guid"))
    secret = db.Column(db.LargeBinary(), nullable=False)
    device_name = db.Column(db.String(32), nullable=False)
    is_valid = db.Column(db.Boolean(), nullable=False, default=False)

    __table_args__ = (
        db.ForeignKeyConstraint([user_guid], [Users.guid], onupdate="CASCADE"),
    )

    def __init__(self,
                 user_guid,
                 secret,
                 device_name,
                 is_valid):
        self.user_guid = user_guid
        self.secret = secret
        self.device_name = device_name
        self.is_valid = is_valid
