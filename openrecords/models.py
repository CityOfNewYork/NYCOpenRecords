
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

class RecordPrivacy:
    # Privacy of uploaded files
    PRIVATE = 0x1
    RELEASED_AND_PRIVATE = 0x2
    RELEASED_AND_PUBLIC = 0x3

class User(UserMixin, db.Model):
    # A staff member from the city
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
            contact_for=None,
            backup_for=None,
            password=None,
            is_staff=False,
            staff_signature=False,
            role=None
    ):

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
        if contact_for and contact_for != '':
            self.contact_for = contact_for
        if backup_for and backup_for != '':
            self.backup_for = backup_for
        if is_staff:
            self.is_staff = is_staff
        if staff_signature:
            self.staff_signature = staff_signature
        if password:
            self.set_password(password)
        if role:
            self.set_role(role)

class Department(db.Model):
    # A city agency
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    date_updated = db.Column(db.DateTime)
    name = db.Column(db.String(), unique=True)
    users = relationship('User', foreign_keys=[User.department_id],
                         post_update=True)  # The list of users in this department

    def __init__(self, name):
        self.name = name
        self.date_created = datetime.now().isoformat()

    def __repr__(self):
        return '<Department %r>' % self.name

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

class Request(db.Model):
    # A request which details paperwork being requested

    __tablename__ = 'request'
    id = db.Column(db.String(100), primary_key=True)
    date_created = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    extended = db.Column(db.Boolean,
                         default=False)  # Has the due date been extended?
    qas = relationship('QA', cascade='all,delete',
                       order_by='QA.date_created.desc()')  # The list of QA units for this request
    status_updated = db.Column(db.DateTime)
    summary = db.Column(db.String(90), nullable=False)
    text = db.Column(db.String(50000),
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
    date_received = db.Column(db.DateTime)
    offline_submission_type = db.Column(db.String())
    prev_status = db.Column(db.String(400))  # The previous status of the request (open, closed, etc.)
    #Adding new privacy option for description field
    description_private=db.Column(db.Boolean, default=True)
    title_private=db.Column(db.Boolean, default=False)
    agency_description=db.Column(db.String(5000))
    agency_description_due_date=db.Column(db.DateTime, default=None, nullable=True)

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
    # Member of a department's staff assigned to a request
    __tablename__ = 'owner'
    id = db.Column(db.Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', uselist=False)
    request_id = db.Column(db.String(100), db.ForeignKey('request.id'))
    request = relationship('Request', foreign_keys=[request_id])
    active = db.Column(db.Boolean,
                       default=True)  # Indicate whether they're still involved in the request or not.
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
    #User who is subscribed to a request

    __tablename__ = 'subscriber'
    __tablename__ = 'subscriber'
    id = db.Column(db.Integer, primary_key=True)
    should_notify = db.Column(db.Boolean,
                              default=True)  # Allows a subscriber to unsubscribe
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', uselist=False)
    request_id = db.Column(db.String(100), db.ForeignKey('request.id'))
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
    # A record that is attached to a particular request. A record can be online (uploaded document, link) or offline.

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
    # A note on a request.

    __tablename__ = 'note'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    text = db.Column(db.String())
    request_id = db.Column(db.String(100), db.ForeignKey(
        'request.id'))  # The request it belongs to.
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'))  # The user who wrote the note. Right now only stored for city staff - otherwise it's an anonymous/ 'requester' note.
    privacy = db.Column(db.Integer, default=0x01)
    due_date = db.Column(db.DateTime, default=None)
    days_after = db.Column(db.Integer, default=None)

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
    # Extends a request
    __tablename__= 'extension'
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
    # Stores all the emails sent out by the application
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