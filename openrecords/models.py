from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from validate_email import validate_email

from . import db


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
    __tablename__ = 'users'
    guid = db.Column(db.String(1000), primary_key=True)
    email = db.Column(db.String(254))
    first_name = db.Column(db.String(32), nullable=False)
    middle_initial = db.Column(db.String(1))
    last_name = db.Column(db.String(64))
    email_validated = db.Column(db.Boolean(), nullable=False)
    terms_of_use_accepted = db.Column(db.Boolean())
    user_type = db.Column(db.String(64))
    title = db.Column(db.String(64))
    company = db.Column(db.String(128))
    phone_number = db.Column(db.String(15))
    fax_number = db.Column(db.String(15))
    mailing_address = db.Column(JSON)

    def __repr__(self): 
        return '<Role %r>'.(self.guid + self.user_type)


