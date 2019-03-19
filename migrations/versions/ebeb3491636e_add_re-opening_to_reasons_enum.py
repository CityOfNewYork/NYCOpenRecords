"""Add Re-Opening to Reasons enum

Revision ID: ebeb3491636e
Revises: dc926c74551d
Create Date: 2018-06-12 20:01:56.529081

"""

# revision identifiers, used by Alembic.
revision = "ebeb3491636e"
down_revision = "b722969f38a6"

from alembic import op
import sqlalchemy as sa

old_options = ("closing", "denial")
new_options = old_options + ("re-opening",)

old_type = sa.Enum(*old_options, name="reason_type")
new_type = sa.Enum(*new_options, name="reason_type")
tmp_type = sa.Enum(*new_options, name="_reason_type")


def upgrade():
    # Create a tempoary "_type" type, convert and drop the "old" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE reasons ALTER COLUMN type TYPE _reason_type"
        " USING type::TEXT::_reason_type"
    )
    old_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "new" type type
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE reasons ALTER COLUMN type TYPE reason_type"
        " USING type::TEXT::reason_type"
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    # Remove re-opening reasons
    op.execute("DELETE FROM reasons WHERE type = 're-opening'")
    # Create a tempoary "_type" type, convert and drop the "new" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE reasons ALTER COLUMN type TYPE _reason_type"
        " USING type::TEXT::_reason_type"
    )
    new_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "old" type type
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE reasons ALTER COLUMN type TYPE reason_type"
        " USING type::TEXT::reason_type"
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)
