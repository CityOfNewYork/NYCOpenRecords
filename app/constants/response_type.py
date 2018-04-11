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
LETTER = "letters"
ENVELOPE = "envelopes"
DETERMINATION = "determinations"
USER_REQUEST_ADDED = "user_request_added"
USER_REQUEST_EDITED = "user_request_edited"
USER_REQUEST_REMOVED = "user_request_removed"

EMAIL_WORKFLOW_TYPES = frozenset((
    NOTE,
    FILE,
    LINK,
    INSTRUCTIONS,
    USER_REQUEST_ADDED,
    USER_REQUEST_EDITED,
    USER_REQUEST_REMOVED
))