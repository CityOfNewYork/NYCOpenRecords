"""
In order to prevent confusion with the Responses inheritance hierarchy,
these constants also serve as the table names and polymorphic identities
for all tables inheriting from Responses.

"""

NOTE = "notes"
FILE = "files"
LINK = "links"
INSTRUCTIONS = "instructions"
EMAIL = "emails"
SMS = "sms"
PUSH = "pushes"
DETERMINATION = "determinations"

EMAIL_WORKFLOW_TYPES = frozenset((
    NOTE,
    FILE,
    LINK,
    INSTRUCTIONS,
    DETERMINATION,
))
