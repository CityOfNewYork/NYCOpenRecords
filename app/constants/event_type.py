USER_CREATED = "user_created"
USER_ADDED = "user_added_to_request"
USER_REMOVED = "user_removed_from_request"
USER_PERM_CHANGED = "user_permissions_changed"
USER_STATUS_CHANGED = "user_status_changed"  # user, admin, super
USER_INFO_EDITED = "user_information_edited"
REQUESTER_INFO_EDITED = "requester_information_edited"
REQ_CREATED = "request_created"
AGENCY_REQ_CREATED = "agency_submitted_request"
REQ_ACKNOWLEDGED = "request_acknowledged"
REQ_STATUS_CHANGED = "request_status_changed"
REQ_EXTENDED = "request_extended"
REQ_CLOSED = "request_closed"
REQ_REOPENED = "request_reopened"
REQ_TITLE_EDITED = "request_title_edited"
REQ_AGENCY_DESC_EDITED = "request_agency_description_edited"
REQ_TITLE_PRIVACY_EDITED = "request_title_privacy_edited"
REQ_AGENCY_DESC_PRIVACY_EDITED = "request_agency_description_privacy_edited"
REQ_AGENCY_DESC_DATE_SET = "request_agency_description_date_set"
EMAIL_NOTIFICATION_SENT = "email_notification_sent"
FILE_ADDED = "file_added"
FILE_EDITED = "file_edited"
FILE_REMOVED = "file_removed"
LINK_ADDED = "link_added"
LINK_EDITED = "link_edited"
LINK_REMOVED = "link_removed"
INSTRUCTIONS_ADDED = "instructions_added"
INSTRUCTIONS_EDITED = "instructions_edited"
INSTRUCTIONS_REMOVED = "instructions_removed"
NOTE_ADDED = "note_added"
NOTE_EDITED = "note_edited"
NOTE_DELETED = "note_deleted"
AGENCY_ACTIVATED = "agency_activated"
CONTACT_EMAIL_SENT = "contact_email_sent"

FOR_REQUEST_HISTORY = [
    USER_ADDED,
    USER_REMOVED,
    USER_PERM_CHANGED,
    REQUESTER_INFO_EDITED,
    REQ_CREATED,
    AGENCY_REQ_CREATED,
    REQ_STATUS_CHANGED,
    REQ_ACKNOWLEDGED,
    REQ_EXTENDED,
    REQ_CLOSED,
    REQ_REOPENED,
    REQ_TITLE_EDITED,
    REQ_AGENCY_DESC_EDITED,
    REQ_TITLE_PRIVACY_EDITED,
    REQ_AGENCY_DESC_PRIVACY_EDITED,
    FILE_ADDED,
    FILE_EDITED,
    FILE_REMOVED,
    LINK_ADDED,
    LINK_EDITED,
    LINK_REMOVED,
    INSTRUCTIONS_ADDED,
    INSTRUCTIONS_EDITED,
    INSTRUCTIONS_REMOVED,
    NOTE_ADDED,
    NOTE_EDITED,
    NOTE_DELETED,
]

RESPONSE_ADDED_TYPES = [
    FILE_ADDED,
    LINK_ADDED,
    INSTRUCTIONS_ADDED,
    NOTE_ADDED,
]
