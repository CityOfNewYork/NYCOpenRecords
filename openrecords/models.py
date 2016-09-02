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
    DUPLICATE_REQUEST = 0x000001
    VIEW_REQUEST_STATUS_PUBLIC = 0x000002
    VIEW_REQUEST_STATUS_ALL = 0x000004
    VIEW_REQUEST_INFO_PUBLIC = 0x000008
    VIEW_REQUEST_INFO_ALL = 0x000016
    ADD_NOTE = 0x000032
    UPLOAD_DOCUMENTS = 0x000064
    VIEW_DOCUMENTS_IMMEDIATELY = 0x000128
    VIEW_REQUESTS_HELPER = 0x000256
    VIEW_REQUESTS_AGENCY = 0x000512
    VIEW_REQUESTS_ALL = 0x001024
    EXTEND_REQUESTS = 0x002048
    CLOSE_REQUESTS = 0x004096
    ADD_HELPERS = 0x008192
    REMOVE_HELPERS = 0x016384
    ACKNOWLEDGE = 0x032768
    CHANGE_REQUEST_POC = 0x065536
    ADMINISTER = 0x131072

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
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')


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


class RecordPrivacy:
    """
    The privacy setting of an uploaded record
    PRIVATE: The file is uploaded but it cannot be viewed by public users and no email notification is sent out
    RELEASED_AND_PRIVATE: File is uploaded but cannot be viewed under the request. An email notification is sent out to
     subscribers.
    RELEASED_AND_PUBLIC: File is uploaded and can be viewed under the request. An email notification is sent to all
    subscribers.
    """
    PRIVATE = 0x1
    RELEASED_AND_PRIVATE = 0x2
    RELEASED_AND_PUBLIC = 0x3


class User(UserMixin, db.Model):
    """User class which can be an agency user or a public user"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String())
    fax = db.Column(db.String())
    address1 = db.Column(db.String(500))
    address2 = db.Column(db.String(500))
    city = db.Column(db.String())
    state = db.Column(db.String())
    zipcode = db.Column(db.String())
    date_created = db.Column(db.DateTime)
    password = db.Column(db.String(255))
    department_id = db.Column(Integer, ForeignKey('department.id',
                                                  use_alter=True,
                                                  name='fk_department'))
    current_department = relationship('Department',
                                      foreign_keys=[department_id],
                                      lazy='joined', uselist=False)
    owners = relationship('Owner')
    subscribers = relationship('Subscriber')
    is_staff = db.Column(db.Boolean, default=False)
    role = db.Column(db.String())

    def __repr__(self):
        return '<User %r>' % self.username

    def __init__(
            self,
            email=None,
            alias=None,
            first_name=None,
            last_name=None,
            phone=None,
            fax=None,
            address1=None,
            address2=None,
            city=None,
            state=None,
            zipcode=None,
            department=None,
            is_staff=False,
            role=None
    ):
        """
        :param email: email which the user uses to login and receive email notifications with (required)
        :param alias: first name and last name combined. Could be removed as a field and just use a property to define
        :param first_name: First name of user (required)
        :param last_name: Last name of user (required)
        :param phone: Phone number of user (optional)
        :param fax: fax number of user (optional)
        :param address1: street address of user (optional)
        :param address2: secondary address of user (optional)
        :param city: city of user (optional)
        :param state: state of user (optional)
        :param zipcode: zipcode of user (optional)
        :param department: department user belongs in (optional)
        :param is_staff: boolean which checks if the user is part of the city or not
        :param role: current roles are: Portal Administrator, Agency Administrator, Agency Foil Officer, Agency Helpers,
        """

        if email and validate_email(email):
            self.email = email
        self.alias = alias
        self.first_name = first_name
        self.last_name = last_name
        if phone and phone != '':
            self.phone = phone
        if fax and fax != '':
            self.fax = fax
        if address1 and address1 != '':
            self.address1 = address1
        if address2 and address2 != '':
            self.address2 = address2
        if city and city != '':
            self.city = city
        if state and state != '':
            self.state = state
        if zipcode and zipcode != '':
            self.zipcode = zipcode
        self.date_created = datetime.now().isoformat()
        if department and department != '':
            self.department_id = department
        if is_staff:
            self.is_staff = is_staff
        if role:
            self.set_role(role)


class Department(db.Model):
    """
    A city department

    :param date_created: the date that the department was added to the databaes
    :param name: the name of the department
    :param users: list of users within department
    :param primary_contact_id: the primary contact for this department
    :param backup_contact_id: the backup contact for this department
    """

    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    name = db.Column(db.String(), unique=True)
    users = relationship('User', foreign_keys=[User.department_id],
                         post_update=True)  # The list of users in this department
    primary_contact_id = db.Column(Integer, ForeignKey('user.id'))
    backup_contact_id = db.Column(Integer, ForeignKey('user.id'))
    primary_contact = relationship(User,
                                   foreign_keys=[primary_contact_id],
                                   primaryjoin=(primary_contact_id == User.id),
                                   uselist=False,
                                   post_update=True)
    backup_contact = relationship(User,
                                  foreign_keys=[backup_contact_id],
                                  primaryjoin=(backup_contact_id == User.id),
                                  uselist=False,
                                  post_update=True)

    def __init__(self, name):
        self.name = name
        self.date_created = datetime.now().isoformat()

    def __repr__(self):
        return '<Department %r>' % self.name


class Request(db.Model):
    """
    A request for a record from the city

    :param date_created: The date the request was created
    :param due_date: The date that the request is due to have a city response by
    :param extended: Boolean that checks if the due date has been extended by any number of days
    :param status_updated: The date the status of a request was updated
    :param title: The title of the request
    :param description: The description of the request
    :param status: The current status of the request
    :param creator_id: The user_id of the request's creator
    :param department_id: The id of the department
    :param offline_submission_type: Indicates whether records should be submitted offline via phone or fax
    :param prev_status: the status previous to the current status
    :param description_private: indicates whether request's description should be viewable by the public
    :param title_private: indicates whether the title of the request should be viewable by the public
    :param agency_description: the agency description that the agency user adds to the request
    :param agency_description_due_date: the date that the agency description is due
    """

    __tablename__ = 'request'
    id = db.Column(db.String(100), primary_key=True)
    date_created = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    extended = db.Column(db.Boolean,
                         default=False)  # Has the due date been extended?
    status_updated = db.Column(db.DateTime)
    title = db.Column(db.String(90), nullable=False)
    description = db.Column(db.String(50000),
                            nullable=False)  # The actual request text.
    owners = relationship('Owner', cascade='all, delete',
                          order_by='Owner.date_created.asc()')
    subscribers = relationship('Subscriber',
                               cascade='all, delete')  # The list of subscribers following this request.
    records = relationship('Record', cascade='all,delete',
                           order_by='Record.date_created.desc()')  # The list of records that have been uploaded for this request.
    notes = relationship('Note', cascade='all,delete',
                         order_by='Note.date_created.desc()')  # The list of notes appended to this request.
    status = db.Column(
        db.String(400))  # The status of the request (open, closed, etc.)
    creator_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'))  # If city staff created it on behalf of the public, otherwise the creator is the subscriber with creator = true
    department_id = db.Column(db.Integer, ForeignKey('department.id',
                                                     name='fk_department'))
    department = relationship('Department', uselist=False)
    offline_submission_type = db.Column(db.String())
    prev_status = db.Column(db.String(400))  # The previous status of the request (open, closed, etc.)
    # Adding new privacy option for description field
    description_private = db.Column(db.Boolean, default=True)
    title_private = db.Column(db.Boolean, default=False)
    agency_description = db.Column(db.String(5000))
    agency_description_due_date = db.Column(db.DateTime, default=None, nullable=True)

    def __init__(
            self,
            id,
            summary,
            text,
            creator_id=None,
            offline_submission_type=None,
            date_received=None,
            agency=None,
            description_private=True,
            title_private=False,
            agency_description=None,
            agency_description_due_date=None
    ):
        self.id = id
        self.summary = summary
        self.text = text
        self.date_created = datetime.now().isoformat()
        self.creator_id = creator_id
        self.offline_submission_type = offline_submission_type
        if date_received and str(type(date_received)) == "<type 'datetime.date'>":
            self.date_received = date_received
        self.department_id = agency
        self.description_private = description_private
        self.titlePrivacy = title_private
        self.agency_description = agency_description
        self.agency_description_due_date = agency_description_due_date

    def __repr__(self):
        return '<Request %r>' % self.summary


class Owner(db.Model):
    """
    The owner of a request assigned by an agency

    :param user_id: the id of the user who is the owner of the request
    :param request_id: the id of the request
    :param reason: the reason that the owner was changed
    :param date_created: the date that the owner is created
    :param is_point_person:
    """
    __tablename__ = 'owner'
    id = db.Column(db.Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', uselist=False)
    request_id = db.Column(db.String(100), db.ForeignKey('request.id'))
    request = relationship('Request', foreign_keys=[request_id])
    reason = db.Column(db.String())  # Reason they were assigned
    date_created = db.Column(db.DateTime)
    date_updated = db.Column(db.DateTime)
    is_point_person = db.Column(db.Boolean)

    def __init__(
            self,
            request_id,
            user_id,
            reason=None,
            is_point_person=False,
    ):
        self.reason = reason
        self.user_id = user_id
        self.request_id = request_id
        self.date_created = datetime.now().isoformat()
        self.date_updated = self.date_created
        self.is_point_person = is_point_person

    def __repr__(self):
        return '<Owner %r>' % self.id


class Subscriber(db.Model):
    """
    A user following a request to receive updates whenever a request is changed

    :param should_notify: indicates whether the user should be notified whenever an update is made to a request
    :param user_id: the id of the user who is subscribing to a request
    :param request_id: the request that the user is subscribed to
    :param date_created: the date that the subscriber was made
    """

    __tablename__ = 'subscriber'
    id = db.Column(db.Integer, primary_key=True)
    should_notify = db.Column(db.Boolean,
                              default=True)  # Allows a subscriber to unsubscribe
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', uselist=False)
    request_id = db.Column(db.String(100), db.ForeignKey('request.id'))
    request = relationship('Request', foreign_keys=[request_id])
    date_created = db.Column(db.DateTime)

    def __init__(
            self,
            request_id,
            user_id,
    ):
        self.user_id = user_id
        self.request_id = request_id
        self.date_created = datetime.now().isoformat()

    def __repr__(self):
        return '<Subscriber %r>' % self.user_i


class Record(db.Model):
    """
    A document that is uploaded to a request
    :param date_created: the date that the record document was uploaded
    :param user_id: the id of the user who uploaded the record
    :param doc_id: the id of the document that was uploaded as part of the record
    :param request_id: the request that the record was uploaded under
    :param description: the description of what the request is
    :param filename: the name of the file that was uploaded
    :param url: the filepath to the directory which the file is stored
    :param download_url: the url where you can download the file
    :param access: how to access the record if not file is not uploaded

    """

    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'))  # The user who uploaded the record, right now only city staff can
    doc_id = db.Column(db.Integer)  # The document ID.
    request_id = db.Column(db.String(100), db.ForeignKey(
        'request.id'))  # The request this record was uploaded for
    description = db.Column(
        db.String(400))  # A short description of what the record is.
    filename = db.Column(
        db.String(400))  # The original name of the file being uploaded.
    url = db.Column(db.String())  # Where it exists on the internet.
    download_url = db.Column(
        db.String())  # Where it can be downloaded on the internet.
    access = db.Column(
        db.String())  # How to access it. Probably only defined on offline docs for now.
    privacy = db.Column(db.Integer, default=RecordPrivacy.PRIVATE)
    release_date = db.Column(db.DateTime, nullable=True)

    def __init__(
            self,
            request_id,
            user_id,
            url=None,
            filename=None,
            doc_id=None,
            description=None,
            access=None,
            privacy=RecordPrivacy.PRIVATE,
            release_date=None
    ):
        self.doc_id = doc_id
        self.request_id = request_id
        self.user_id = user_id
        self.date_created = datetime.now().isoformat()
        self.description = description
        self.url = url
        self.filename = filename
        self.access = access
        self.privacy = privacy
        self.release_date = release_date


def __repr__(self):
    return '<Record %r>' % self.description


class Note(db.Model):
    """
    A note made by a user for other users to see under a request's responses

    :param date_created: the date that the note was created
    :param text: the text content of the request
    :param request_id: the request that the note is associated with
    :param user_id: the user that posted the note
    """

    __tablename__ = 'note'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    text = db.Column(db.String())
    request_id = db.Column(db.String(100), db.ForeignKey(
        'request.id'))  # The request it belongs to.
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'))  # The user who wrote the note. Right now only stored for city staff - otherwise it's an anonymous/ 'requester' note.

    def __init__(
            self,
            request_id,
            text,
            user_id,
            privacy=0x01,
            due_date=None,
            days_after=None
    ):
        self.text = text
        self.request_id = request_id
        self.user_id = user_id
        self.date_created = datetime.now().isoformat()
        self.privacy = privacy
        self.due_date = due_date
        self.days_after = days_after

    def __repr__(self):
        return '<Note %r>' % self.text


class Extension(db.Model):
    """
    An extension made to a request

    :param date_created: the date the extension was made
    :param request_id: the id of the request that the extension was made for
    :param user_id: the id of the user who made the extension
    :param due_date: the new date the extension is due
    :param days_after: the amount of days the request is extended by. set to -1 if a custom due date is set
    """

    __tablename__ = 'extension'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    request_id = db.Column(db.String(100), db.ForeignKey('request.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    due_date = db.Column(db.DateTime, default=None)
    days_after = db.Column(db.Integer, default=None)

    def __init__(
            self,
            request_id,
            user_id,
            due_date=None,
            days_after=None
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.date_created = datetime.now().isoformat()
        self.due_date = due_date
        self.days_after = days_after


def __repr__(self):
    return '<Note %r>' % self.text


class Email(db.Model):
    """
    Content and header information of an email

    :param request_id: the id of the request that the email was sent out for
    :param recipient: the recipient of the email
    :param subject: the subject of the email
    :param time_sent: when the email was sent
    :param email_content: a jsonified dictionary containing the text of the email and other fields relevant to the email
    """
    __tablename__ = 'email_notification'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(20), db.ForeignKey(
        'request.id'
    ), nullable=False)
    recipient = db.Column(db.Integer(), db.ForeignKey(
        'user.id'
    ), nullable=False)
    subject = db.Column(db.String(5000), nullable=False)
    time_sent = db.Column(db.DateTime, nullable=False)
    email_content = db.Column(JSON, nullable=False)

    def __init__(
            self,
            request_id,
            recipient,
            subject=None,
            time_sent=None,
            email_content=None
    ):
        self.request_id = request_id
        self.recipient = recipient
        self.subject = subject
        self.time_sent = time_sent
        self.email_content = email_content


# Jonathan Started Here

# Agency
# Employer ID Number (EIN) Primary key, 3 digit int
# Agency name - String (64)
# Next Request Number - int sequence starting at 1 to 99999 (each agency has its own sequence, next number in the sequence)
# Agency default email - String
# Agency appeal email - String

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
    user_guid = db.Column(db.String(1000), db.ForeignKey("users.guid"))
    request_id = db.Column(db.String(19), db.ForeignKey("requests.id"))
    permission = db.Column(db.Integer)
