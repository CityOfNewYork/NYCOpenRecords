"""Add primary keys to users, user_requests, and agency_users

Revision ID: b12d4ba1cfd4
Revises: 838a6ad16cf4
Create Date: 2019-03-18 16:44:35.911810

"""

# revision identifiers, used by Alembic.
revision = "b12d4ba1cfd4"
down_revision = "aeb1852855b4"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

request_user_type_enum = postgresql.ENUM(
    "requester", "agency", name="request_user_type", create_type=False
)


def upgrade():
    # Add primary key to the Users
    op.create_table(
        "users_new",
        sa.Column("guid", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_super", sa.Boolean(), nullable=True, default=False),
        sa.Column("first_name", sa.String(length=32), nullable=False),
        sa.Column("middle_initial", sa.String(length=1), nullable=True),
        sa.Column("last_name", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("email_validated", sa.Boolean(), nullable=False, default=True),
        sa.Column("terms_of_use_accepted", sa.Boolean(), nullable=True, default=True),
        sa.Column("title", sa.String(length=64), nullable=True),
        sa.Column("organization", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=25), nullable=True),
        sa.Column("fax_number", sa.String(length=25), nullable=True),
        sa.Column(
            "mailing_address", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("notification_email", sa.String(length=254), nullable=True),
        sa.Column("session_id", sa.String(length=254), nullable=True),
        sa.Column("signature", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("has_nyc_account", sa.Boolean(), nullable=True),
        sa.Column("is_anonymous_requester", sa.Boolean(), nullable=True),
        sa.Column("is_nyc_employee", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("guid"),
    )
    op.execute(
        "create index if not exists users_lower_idx on users_new (lower(email::text));"
    )
    op.execute(
        """INSERT INTO users_new (guid, is_super, first_name, middle_initial, last_name, email, email_validated, 
                    terms_of_use_accepted, title, organization, phone_number, fax_number, mailing_address, 
                    notification_email, session_id, signature, active, has_nyc_account, is_anonymous_requester, 
                    is_nyc_employee)
                    
                    SELECT guid,
                           is_super,
                           first_name,
                           middle_initial,
                           last_name,
                           email,
                           email_validated,
                           terms_of_use_accepted,
                           title,
                           organization,
                           phone_number,
                           fax_number,
                           mailing_address,
                           notification_email,
                           session_id,
                           signature,
                           active,
                           has_nyc_account,
                           is_anonymous_requester,
                           is_nyc_employee
                    FROM users;"""
    )
    op.drop_constraint(
        "agency_users_user_guid_fkey", "agency_users", type_="foreignkey"
    )
    op.execute(
        """ALTER TABLE agency_users DROP CONSTRAINT IF EXISTS agency_users_user_guid_fkey1;"""
    )
    op.drop_constraint("events_user_guid_fkey", "events", type_="foreignkey")
    op.drop_constraint(
        "user_requests_user_guid_fkey", "user_requests", type_="foreignkey"
    )
    op.drop_table("users")
    op.create_table(
        "users",
        sa.Column("guid", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_super", sa.Boolean(), nullable=False, default=False),
        sa.Column("first_name", sa.String(length=32), nullable=False),
        sa.Column("middle_initial", sa.String(length=1), nullable=True),
        sa.Column("last_name", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("email_validated", sa.Boolean(), nullable=False, default=True),
        sa.Column("terms_of_use_accepted", sa.Boolean(), nullable=True, default=True),
        sa.Column("title", sa.String(length=64), nullable=True),
        sa.Column("organization", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=25), nullable=True),
        sa.Column("fax_number", sa.String(length=25), nullable=True),
        sa.Column(
            "mailing_address", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("notification_email", sa.String(length=254), nullable=True),
        sa.Column("session_id", sa.String(length=254), nullable=True),
        sa.Column("signature", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("has_nyc_account", sa.Boolean(), nullable=True),
        sa.Column("is_anonymous_requester", sa.Boolean(), nullable=True),
        sa.Column("is_nyc_employee", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("guid"),
    )
    op.execute(
        "create index if not exists users_lower_idx on users (lower(email::text));"
    )
    op.execute(
        """INSERT INTO users (guid, is_super, first_name, middle_initial, last_name, email, email_validated, 
                        terms_of_use_accepted, title, organization, phone_number, fax_number, mailing_address, 
                        notification_email, session_id, signature, active, has_nyc_account, is_anonymous_requester, 
                        is_nyc_employee)

                        SELECT guid,
                               is_super,
                               first_name,
                               middle_initial,
                               last_name,
                               email,
                               email_validated,
                               terms_of_use_accepted,
                               title,
                               organization,
                               phone_number,
                               fax_number,
                               mailing_address,
                               notification_email,
                               session_id,
                               signature,
                               active,
                               has_nyc_account,
                               is_anonymous_requester,
                               is_nyc_employee
                        FROM users_new;"""
    )
    op.drop_table("users_new")
    op.create_foreign_key(
        None, "agency_users", "users", ["user_guid"], ["guid"], onupdate="CASCADE"
    )
    op.create_foreign_key(
        None, "events", "users", ["user_guid"], ["guid"], onupdate="CASCADE"
    )
    op.create_foreign_key(
        None, "user_requests", "users", ["user_guid"], ["guid"], onupdate="CASCADE"
    )

    # Add primary key to the Users
    op.create_table(
        "user_requests_new",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=19), nullable=False),
        sa.Column("request_user_type", request_user_type_enum, nullable=True),
        sa.Column("permissions", sa.BigInteger(), nullable=True),
        sa.Column("point_of_contact", sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("user_guid", "request_id"),
    )
    op.execute(
        """INSERT INTO user_requests_new (user_guid, request_id, permissions, 
                  request_user_type, point_of_contact)
                  SELECT user_guid, request_id, permissions, request_user_type, point_of_contact FROM user_requests;"""
    )
    op.drop_table("user_requests")
    op.create_table(
        "user_requests",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=19), nullable=False),
        sa.Column("request_user_type", request_user_type_enum, nullable=True),
        sa.Column("permissions", sa.BigInteger(), nullable=True),
        sa.Column("point_of_contact", sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("user_guid", "request_id"),
    )
    op.execute(
        """INSERT INTO user_requests (user_guid, request_id, permissions, 
                  request_user_type, point_of_contact)
                  SELECT user_guid, request_id, permissions, request_user_type, point_of_contact 
                  FROM user_requests_new;"""
    )
    op.drop_table("user_requests_new")

    # Add primary key to AgencyUsers
    op.create_table(
        "agency_users_new",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("agency_ein", sa.String(length=4), nullable=False),
        sa.Column("is_agency_active", sa.Boolean(), nullable=False),
        sa.Column("is_agency_admin", sa.Boolean(), nullable=False),
        sa.Column("is_primary_agency", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["agency_ein"], ["agencies.ein"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("user_guid", "agency_ein"),
    )
    op.execute(
        """INSERT INTO agency_users_new (user_guid, agency_ein, is_agency_active, 
                  is_agency_admin, is_primary_agency)
                  SELECT
                    user_guid,
                    agency_ein,
                    is_agency_active,
                    is_agency_admin,
                    is_primary_agency
                  FROM agency_users;"""
    )
    op.drop_table("agency_users")
    op.create_table(
        "agency_users",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("agency_ein", sa.String(length=4), nullable=False),
        sa.Column("is_agency_active", sa.Boolean(), nullable=False),
        sa.Column("is_agency_admin", sa.Boolean(), nullable=False),
        sa.Column("is_primary_agency", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["agency_ein"], ["agencies.ein"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("user_guid", "agency_ein"),
    )
    op.execute(
        """INSERT INTO agency_users (user_guid, agency_ein, is_agency_active, 
                  is_agency_admin, is_primary_agency)
                  SELECT
                    user_guid,
                    agency_ein,
                    is_agency_active,
                    is_agency_admin,
                    is_primary_agency
                  FROM agency_users_new;"""
    )
    op.drop_table("agency_users_new")


def downgrade():
    op.create_table(
        "users_new",
        sa.Column("guid", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_super", sa.Boolean(), nullable=True, default=False),
        sa.Column("first_name", sa.String(length=32), nullable=False),
        sa.Column("middle_initial", sa.String(length=1), nullable=True),
        sa.Column("last_name", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("email_validated", sa.Boolean(), nullable=False, default=True),
        sa.Column("terms_of_use_accepted", sa.Boolean(), nullable=True, default=True),
        sa.Column("title", sa.String(length=64), nullable=True),
        sa.Column("organization", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=25), nullable=True),
        sa.Column("fax_number", sa.String(length=25), nullable=True),
        sa.Column(
            "mailing_address", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("notification_email", sa.String(length=254), nullable=True),
        sa.Column("session_id", sa.String(length=254), nullable=True),
        sa.Column("signature", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("has_nyc_account", sa.Boolean(), nullable=True),
        sa.Column("is_anonymous_requester", sa.Boolean(), nullable=True),
        sa.Column("is_nyc_employee", sa.Boolean(), nullable=True),
    )
    op.execute(
        "create index if not exists users_lower_idx on users_new (lower(email::text));"
    )
    op.execute(
        """INSERT INTO users_new (guid, is_super, first_name, middle_initial, last_name, email, email_validated,
                        terms_of_use_accepted, title, organization, phone_number, fax_number, mailing_address, 
                        notification_email, session_id, signature, active, has_nyc_account, is_anonymous_requester, 
                        is_nyc_employee)
    
                        SELECT guid,
                               is_super,
                               first_name,
                               middle_initial,
                               last_name,
                               email,
                               email_validated,
                               terms_of_use_accepted,
                               title,
                               organization,
                               phone_number,
                               fax_number,
                               mailing_address,
                               notification_email,
                               session_id,
                               signature,
                               active,
                               has_nyc_account,
                               is_anonymous_requester,
                               is_nyc_employee
                        FROM users;"""
    )
    op.drop_constraint(
        "agency_users_user_guid_fkey", "agency_users", type_="foreignkey"
    )
    op.drop_constraint("events_user_guid_fkey", "events", type_="foreignkey")
    op.drop_constraint(
        "user_requests_user_guid_fkey", "user_requests", type_="foreignkey"
    )
    op.drop_table("users")
    op.create_table(
        "users",
        sa.Column("guid", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_super", sa.Boolean(), nullable=False, default=False),
        sa.Column("first_name", sa.String(length=32), nullable=False),
        sa.Column("middle_initial", sa.String(length=1), nullable=True),
        sa.Column("last_name", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("email_validated", sa.Boolean(), nullable=False, default=True),
        sa.Column("terms_of_use_accepted", sa.Boolean(), nullable=True, default=True),
        sa.Column("title", sa.String(length=64), nullable=True),
        sa.Column("organization", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=25), nullable=True),
        sa.Column("fax_number", sa.String(length=25), nullable=True),
        sa.Column(
            "mailing_address", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("notification_email", sa.String(length=254), nullable=True),
        sa.Column("session_id", sa.String(length=254), nullable=True),
        sa.Column("signature", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("has_nyc_account", sa.Boolean(), nullable=True),
        sa.Column("is_anonymous_requester", sa.Boolean(), nullable=True),
        sa.Column("is_nyc_employee", sa.Boolean(), nullable=True),
    )
    op.execute(
        "create index if not exists users_lower_idx on users (lower(email::text));"
    )
    op.execute(
        """INSERT INTO users (guid, is_super, first_name, middle_initial, last_name, email, email_validated, 
                            terms_of_use_accepted, title, organization, phone_number, fax_number, mailing_address, 
                            notification_email, session_id, signature, active, has_nyc_account, is_anonymous_requester, 
                            is_nyc_employee)

                            SELECT guid,
                                   is_super,
                                   first_name,
                                   middle_initial,
                                   last_name,
                                   email,
                                   email_validated,
                                   terms_of_use_accepted,
                                   title,
                                   organization,
                                   phone_number,
                                   fax_number,
                                   mailing_address,
                                   notification_email,
                                   session_id,
                                   signature,
                                   active,
                                   has_nyc_account,
                                   is_anonymous_requester,
                                   is_nyc_employee
                            FROM users_new;"""
    )
    op.drop_table("users_new")
    op.create_foreign_key(
        None, "agency_users", "users", ["user_guid"], ["guid"], onupdate="CASCADE"
    )
    op.create_foreign_key(
        None, "events", "users", ["user_guid"], ["guid"], onupdate="CASCADE"
    )
    op.create_foreign_key(
        None, "user_requests", "users", ["user_guid"], ["guid"], onupdate="CASCADE"
    )

    op.create_table(
        "user_requests_new",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=19), nullable=False),
        sa.Column("request_user_type", request_user_type_enum, nullable=True),
        sa.Column("permissions", sa.BigInteger(), nullable=True),
        sa.Column("point_of_contact", sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
    )
    op.execute(
        """INSERT INTO user_requests_new (user_guid, request_id, permissions, 
                      request_user_type, point_of_contact)
                      SELECT user_guid, request_id, permissions, request_user_type, point_of_contact FROM user_requests;"""
    )
    op.drop_table("user_requests")
    op.create_table(
        "user_requests",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=19), nullable=False),
        sa.Column("request_user_type", request_user_type_enum, nullable=True),
        sa.Column("permissions", sa.BigInteger(), nullable=True),
        sa.Column("point_of_contact", sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
    )
    op.execute(
        """INSERT INTO user_requests (user_guid, request_id, permissions, 
                      request_user_type, point_of_contact)
                      SELECT user_guid, request_id, permissions, request_user_type, point_of_contact 
                      FROM user_requests_new;"""
    )
    op.drop_table("user_requests_new")

    op.create_table(
        "agency_users_new",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("agency_ein", sa.String(length=4), nullable=False),
        sa.Column("is_agency_active", sa.Boolean(), nullable=False),
        sa.Column("is_agency_admin", sa.Boolean(), nullable=False),
        sa.Column("is_primary_agency", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["agency_ein"], ["agencies.ein"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
    )
    op.execute(
        """INSERT INTO agency_users_new (user_guid, agency_ein, is_agency_active, 
                  is_agency_admin, is_primary_agency)
                  SELECT
                    user_guid,
                    agency_ein,
                    is_agency_active,
                    is_agency_admin,
                    is_primary_agency
                  FROM agency_users;"""
    )
    op.drop_table("agency_users")
    op.create_table(
        "agency_users",
        sa.Column("user_guid", sa.String(length=64), nullable=False),
        sa.Column("agency_ein", sa.String(length=4), nullable=False),
        sa.Column("is_agency_active", sa.Boolean(), nullable=False),
        sa.Column("is_agency_admin", sa.Boolean(), nullable=False),
        sa.Column("is_primary_agency", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["agency_ein"], ["agencies.ein"]),
        sa.ForeignKeyConstraint(["user_guid"], ["users.guid"], onupdate="CASCADE"),
    )
    op.execute(
        """INSERT INTO agency_users (user_guid, agency_ein, is_agency_active, 
                  is_agency_admin, is_primary_agency)
                  SELECT
                    user_guid,
                    agency_ein,
                    is_agency_active,
                    is_agency_admin,
                    is_primary_agency
                  FROM agency_users_new;"""
    )
    op.drop_table("agency_users_new")
