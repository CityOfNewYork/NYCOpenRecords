"""Drop the Users.agency_ein column.
 Revision ID: 24e110b4489b
Revises: 9908a9bf1dbd
Create Date: 2017-07-06 22:16:44.862690
 """

# revision identifiers, used by Alembic.
revision = "24e110b4489b"
down_revision = "9908a9bf1dbd"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column("users", "agency_ein")
    op.drop_column("users", "is_agency_active")
    op.drop_column("users", "is_agency_admin")


def downgrade():
    op.add_column(
        "users",
        sa.Column("is_agency_admin", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_agency_active", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
    )
    op.add_column("users", sa.Column("agency_ein", sa.String(length=4), nullable=True))
