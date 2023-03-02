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
REQ_DENIED = "request_denied"
REQ_STATUS_CHANGED = "request_status_changed"
REQ_EXTENDED = "request_extended"
REQ_CLOSED = "request_closed"
REQ_REOPENED = "request_reopened"
REQ_TITLE_EDITED = "request_title_edited"
REQ_AGENCY_REQ_SUM_EDITED = "request_agency_request_summary_edited"
REQ_TITLE_PRIVACY_EDITED = "request_title_privacy_edited"
REQ_AGENCY_REQ_SUM_PRIVACY_EDITED = "request_agency_request_summary_privacy_edited"
REQ_AGENCY_REQ_SUM_DATE_SET = "request_agency_request_summary_date_set"
REQ_POINT_OF_CONTACT_ADDED = "request_point_of_contact_added"
REQ_POINT_OF_CONTACT_REMOVED = "request_point_of_contact_removed"
EMAIL_NOTIFICATION_SENT = "email_notification_sent"
FILE_ADDED = "file_added"
FILE_EDITED = "file_edited"
FILE_PRIVACY_EDITED = "file_privacy_edited"
FILE_REPLACED = "file_replaced"
FILE_REMOVED = "file_removed"
LINK_ADDED = "link_added"
LINK_EDITED = "link_edited"
LINK_PRIVACY_EDITED = "link_privacy_edited"
LINK_REMOVED = "link_removed"
INSTRUCTIONS_ADDED = "instructions_added"
INSTRUCTIONS_EDITED = "instructions_edited"
INSTRUCTIONS_PRIVACY_EDITED = "instructions_privacy_edited"
INSTRUCTIONS_REMOVED = "instructions_removed"
NOTE_ADDED = "note_added"
NOTE_EDITED = "note_edited"
NOTE_PRIVACY_EDITED = "note_privacy_edited"
NOTE_REMOVED = "note_removed"
AGENCY_ACTIVATED = "agency_activated"
AGENCY_DEACTIVATED = "agency_deactivated"
AGENCY_USER_ACTIVATED = "agency_user_activated"
AGENCY_USER_DEACTIVATED = "agency_user_deactivated"
CONTACT_EMAIL_SENT = "contact_email_sent"
USER_LOGIN = "user_logged_in"
USER_FAILED_LOG_IN = "user_failed_login"
USER_AUTHORIZED = "user_authorized"
USER_LOGGED_OUT = "user_logged_out"
USER_FAILED_LOG_OUT = "user_failed_log_out"
USER_MADE_AGENCY_ADMIN = "user_made_agency_admin"
USER_MADE_AGENCY_USER = "user_made_agency_user"
USER_MADE_SUPER_USER = "user_made_super_user"
USER_REMOVED_FROM_SUPER = "user_removed_from_super"
USER_PROFILE_UPDATED = "user_profile_updated"
ACKNOWLEDGMENT_LETTER_CREATED = 'acknowledgment_letter_created'
DENIAL_LETTER_CREATED = 'denial_letter_created'
CLOSING_LETTER_CREATED = 'closing_letter_created'
EXTENSION_LETTER_CREATED = 'extension_letter_created'
ENVELOPE_CREATED = 'envelope_created'
RESPONSE_LETTER_CREATED = 'response_letter_created'
REOPENING_LETTER_CREATED = 'reopening_letter_created'
MFA_DEVICE_ADDED = 'mfa_device_added'
MFA_DEVICE_REMOVED = 'mfa_device_removed'

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
    REQ_DENIED,
    REQ_REOPENED,
    REQ_TITLE_EDITED,
    REQ_AGENCY_REQ_SUM_EDITED,
    REQ_TITLE_PRIVACY_EDITED,
    REQ_AGENCY_REQ_SUM_PRIVACY_EDITED,
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
    NOTE_REMOVED,
    ENVELOPE_CREATED,
    RESPONSE_LETTER_CREATED
]

RESPONSE_ADDED_TYPES = [
    FILE_ADDED,
    LINK_ADDED,
    INSTRUCTIONS_ADDED,
    NOTE_ADDED,
]

RESPONSE_EDITED_TYPES = [
    FILE_EDITED,
    FILE_REPLACED,
    FILE_PRIVACY_EDITED,
    LINK_EDITED,
    LINK_PRIVACY_EDITED,
    INSTRUCTIONS_EDITED,
    INSTRUCTIONS_PRIVACY_EDITED,
    NOTE_ADDED,
    NOTE_PRIVACY_EDITED
]

RESPONSE_REMOVED_TYPES = [
    FILE_REMOVED,
    LINK_REMOVED,
    INSTRUCTIONS_REMOVED,
    NOTE_REMOVED
]

SYSTEM_TYPES = [
    AGENCY_ACTIVATED,
    AGENCY_DEACTIVATED,
    AGENCY_USER_ACTIVATED,
    AGENCY_USER_DEACTIVATED,
    CONTACT_EMAIL_SENT,
    USER_LOGIN,
    USER_FAILED_LOG_IN,
    USER_AUTHORIZED,
    USER_LOGGED_OUT,
    USER_FAILED_LOG_OUT,
    USER_MADE_AGENCY_ADMIN,
    USER_MADE_AGENCY_USER,
    USER_PROFILE_UPDATED
]
