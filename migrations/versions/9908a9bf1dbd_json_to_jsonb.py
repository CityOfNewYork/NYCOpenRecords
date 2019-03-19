"""JSON to JSONB

Revision ID: 9908a9bf1dbd
Revises: 971f341c0204
Create Date: 2017-06-02 18:16:00.920315

"""

# revision identifiers, used by Alembic.
revision = "9908a9bf1dbd"
down_revision = "cf62ec87d973"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column(
        "agencies",
        "agency_features",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "users",
        "mailing_address",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "requests",
        "privacy",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "events",
        "previous_value",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "events",
        "new_value",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "agencies",
        "agency_features",
        type_=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "users",
        "mailing_address",
        type_=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "requests",
        "privacy",
        type_=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "events",
        "previous_value",
        type_=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "events",
        "new_value",
        type_=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
