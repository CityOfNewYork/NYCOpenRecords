from app.constants import response_type, determination_type, event_type

ACKNOWLEDGMENT_PERIOD_LENGTH = 5

CATEGORIES = [
    ('', 'All'),
    ('Business', 'Business'),
    ('Civic Services', 'Civic Services'),
    ('Culture & Recreation', 'Culture & Recreation'),
    ('Education', 'Education'),
    ('Environment', 'Environment'),
    ('Health', 'Health'),
    ('Housing & Development', 'Housing & Development'),
    ('Public Safety', 'Public Safety'),
    ('Social Services', 'Social Services'),
    ('Transportation', 'Transportation')
]

STATES = [
    ('', ''),
    ('AL', 'Alabama'),
    ('AK', 'Alaska'),
    ('AZ', 'Arizona'),
    ('AR', 'Arkansas'),
    ('CA', 'California'),
    ('CO', 'Colorado'),
    ('CT', 'Connecticut'),
    ('DE', 'Delaware'),
    ('DC', 'District Of Columbia'),
    ('FL', 'Florida'),
    ('GA', 'Georgia'),
    ('HI', 'Hawaii'),
    ('ID', 'Idaho'),
    ('IL', 'Illinois'),
    ('IN', 'Indiana'),
    ('IA', 'Iowa'),
    ('KS', 'Kansas'),
    ('KY', 'Kentucky'),
    ('LA', 'Louisiana'),
    ('ME', 'Maine'),
    ('MD', 'Maryland'),
    ('MA', 'Massachusetts'),
    ('MI', 'Michigan'),
    ('MN', 'Minnesota'),
    ('MS', 'Mississippi'),
    ('MO', 'Missouri'),
    ('MT', 'Montana'),
    ('NE', 'Nebraska'),
    ('NV', 'Nevada'),
    ('NH', 'New Hampshire'),
    ('NJ', 'New Jersey'),
    ('NM', 'New Mexico'),
    ('NY', 'New York'),
    ('NC', 'North Carolina'),
    ('ND', 'North Dakota'),
    ('OH', 'Ohio'),
    ('OK', 'Oklahoma'),
    ('OR', 'Oregon'),
    ('PA', 'Pennsylvania'),
    ('PR', 'Puerto Rico'),
    ('RI', 'Rhode Island'),
    ('SC', 'South Carolina'),
    ('SD', 'South Dakota'),
    ('TN', 'Tennessee'),
    ('TX', 'Texas'),
    ('UT', 'Utah'),
    ('VT', 'Vermont'),
    ('VA', 'Virginia'),
    ('WA', 'Washington'),
    ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'),
    ('WY', 'Wyoming')
]

USER_ID_DELIMITER = '|'

UPDATED_FILE_DIRNAME = 'updated'
DELETED_FILE_DIRNAME = 'deleted'

RESPONSES_INCREMENT = 10
EVENTS_INCREMENT = 10

DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS = 20

ES_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"  # strict_date_hour_minute_second

EMAIL_TEMPLATE_FOR_TYPE = {
    response_type.FILE: "email_response_file.html",
    response_type.LINK: "email_response_link.html",
    response_type.NOTE: "email_response_note.html",
    response_type.INSTRUCTIONS: "email_response_instruction.html",
    response_type.USER_REQUEST_ADDED: "email_user_request_added.html",
    response_type.USER_REQUEST_EDITED: "email_user_request_edited.html",
    response_type.USER_REQUEST_REMOVED: "email_user_request_deleted.html",
    determination_type.ACKNOWLEDGMENT: "email_response_acknowledgment.html",
    determination_type.DENIAL: "email_response_denial.html",
    determination_type.CLOSING: "email_response_closing.html",
    determination_type.QUICK_CLOSING: "email_response_quick_closing.html",
    determination_type.EXTENSION: "email_response_extension.html",
    determination_type.REOPENING: "email_response_reopening.html"
}

EMAIL_TEMPLATE_FOR_EVENT = {
    event_type.ACKNOWLEDGMENT_LETTER_CREATED: "email_event_acknowledgment_letter_created.html",
    event_type.DENIAL_LETTER_CREATED: "email_event_denial_letter_created.html",
    event_type.CLOSING_LETTER_CREATED: "email_event_closing_letter_created.html",
    event_type.EXTENSION_LETTER_CREATED: "email_event_extension_letter_created.html",
    event_type.ENVELOPE_CREATED: "email_event_envelope_created.html",
    event_type.RESPONSE_LETTER_CREATED: "email_event_response_letter_created.html",
    event_type.REOPENING_LETTER_CREATED: "email_event_reopening_letter_created.html"
}

OPENRECORDS_DL_EMAIL = "openrecords@records.nyc.gov"

TINYMCE_EDITABLE_P_TAG = '<p id="editable-p">&nbsp;</p>'

CONFIRMATION_EMAIL_HEADER_TO_REQUESTER = "The following will be emailed to the Requester:"
CONFIRMATION_EMAIL_HEADER_TO_AGENCY = "The following will be emailed to all Assigned Users:"
CONFIRMATION_LETTER_HEADER_TO_REQUESTER = "The following will be mailed to the Requester:"

HIDDEN_AGENCIES = [
    '002Q',  # Mayor's Office of Technology and Innovation - OS-1269
]