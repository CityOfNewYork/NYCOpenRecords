"""Modify 'type' enum to include letters and envelopes

Revision ID: 22b97712d5db
Revises: b3c0c76ac2e6
Create Date: 2018-04-10 13:21:33.718643

"""

# revision identifiers, used by Alembic.
revision = "22b97712d5db"
down_revision = "b3c0c76ac2e6"

from alembic import op
import sqlalchemy as sa

old_options = ("notes", "links", "files", "instructions", "determinations", "emails")
new_options = old_options + ("letters", "envelopes")

old_type = sa.Enum(*old_options, name="type")
new_type = sa.Enum(*new_options, name="type")
tmp_type = sa.Enum(*new_options, name="_type")


def upgrade():
    # Create a tempoary "_type" type, convert and drop the "old" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE responses ALTER COLUMN type TYPE _type" " USING type::TEXT::_type"
    )
    old_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "new" type type
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE responses ALTER COLUMN type TYPE type" " USING type::TEXT::type"
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    # Convert 'envelopes' and 'letters' type into 'note'

    op.execute(
        "UPDATE responses SET type = 'note' WHERE type IN \('letters', 'envelopes'\)"
    )
    # Create a tempoary "_type" type, convert and drop the "new" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE responses ALTER COLUMN type TYPE _type" " USING type::TEXT::_type"
    )
    new_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "old" type type
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE responses ALTER COLUMN type TYPE type" " USING type::TEXT::type"
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)
