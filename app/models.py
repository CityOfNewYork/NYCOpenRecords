import re
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy import and_, or_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, \
    check_password_hash
from . import db
from flask_login import UserMixin, AnonymousUserMixin
from validate_email import validate_email


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

# Jonathan Started Here

class Agency(db.Model):
    __tablename__ = 'agency'
    ein = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    next_request_number = db.Column(db.Integer(), db.Sequence('request_seq'))
    default_email = db.Column(db.String(254))
    appeal_email = db.Column(db.String(254))

    def __repr__(self):
        return '<Agency %r>' % self.name

class UserRequest(db.Model):
    __tablename__ = 'user_request'
    user_guid = db.Column(db.String(1000), db.ForeignKey("user.guid"))
    request_id = db.Column(db.String(19), db.ForeignKey("request.id"))
    permission = db.Column(db.Integer)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    guid = db.Column(db.String(1000), primary_key=True)
    password_hash = db.Column(db.String(255))
    user_type = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(254))
    first_name = db.Column(db.String(32), nullable=False)
    middle_initial = db.Column(db.String(1))
    last_name = db.Column(db.String(64), nullable=False)
    email_validated = db.Column(db.Boolean(), nullable=False)
    terms_of_use_accepted = db.Column(db.Boolean(), nullable=False)
    title = db.Column(db.String(64))
    company = db.Column(db.String(128))
    phone_number = db.Column(db.String(15))
    fax_number = db.Column(db.String(15))
    mailing_address = db.Column(JSON)

    def __repr__(self):
        return '<User %r>' % self.guid


class Request(db.Model):
    __tablename__ = 'request'
    id = db.Column(db.String(19), primary_key=True)
    title = db.Column(db.String(90))
    description = db.Column(db.String(5000))
    agency = db.Column(db.Integer, db.ForeignKey('agency.ein'))
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    date_submitted = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    # submission = db.Column(db.Enum('fill in types here', name='submission_type'))
    submission = db.Column(db.String(30))
    current_status = db.Column(db.Enum('Open', 'In Progress', 'Due Soon', 'Overdue', 'Closed', 'Re-Opened',
                                       name='statuses'))
    visibility = db.Column(JSON)

    def __repr__(self):
        return '<Request %r>' % self.id


class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.String(100), primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('request.id'))
    user_id = db.Column(db.String(1000), db.ForeignKey('user.guid'))
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'))
    type = db.Column(db.String(30))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    previous_response_value = db.Column(db.String(5000))
    new_responpse_vvalue = db.Column(db.String(50000))

    def __repr__(self):
        return '<Event %r>' % self.id


class Response(db.Model):
    __tablename__ = 'response'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(19), db.ForeignKey('request.id'))
    type = db.Column(db.String(30))
    date_modified = db.Column(db.DateTime)
    content = db.Column(JSON)
    privacy = db.Column(db.String(7))

    def __repr__(self):
        return '<Response %r>' % self.id


# do we care about what users work at what agency?
# get submission types for Request table
# finish up roles and permissions