"""Remove auth_user_type

Revision ID: 838a6ad16cf4
Revises: 89d3f2e347f1
Create Date: 2018-12-28 20:00:00.649860

"""

# revision identifiers, used by Alembic.
revision = "838a6ad16cf4"
down_revision = "89d3f2e347f1"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_column("users", "auth_user_type")


def downgrade():
    op.add_column(
        "users",
        sa.Column(
            "auth_user_type",
            postgresql.ENUM(
                "Saml2In:NYC Employees",
                "LDAP:NYC Employees",
                "FacebookSSO",
                "MSLiveSSO",
                "YahooSSO",
                "LinkedInSSO",
                "GoogleSSO",
                "EDIRSSO",
                "AnonymousUser",
                name="auth_user_type",
            ),
            autoincrement=False,
            nullable=False,
        ),
    )
