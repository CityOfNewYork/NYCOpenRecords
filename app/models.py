from sqlalchemy.dialects.postgresql import JSON

from app import db


class User(db.Model):
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
        return '<Role {0!r}>'.format(self.guid + self.user_type)
