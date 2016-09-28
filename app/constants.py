ACKNOWLEDGEMENT_DAYS_DUE = 5

EVENT_TYPE = {
    "user_added": "user_added",
    "user_permissions_changed": "user_permissions_changed",
    "user_information_edited": "user_information_edited",
    "request_created": "request_created",
    "request_acknowledged": "request_acknowledged",
    "request_status_changed": "request_status_changed",
    "request_extended": "request_extended",
    "request_closed": "request_closed",
    "request_title_edited": "request_title_edited",
    "request_agency_description_edited": "request_agency_description_edited",
    "request_title_privacy_edited": "request_title_privacy_edited",
    "request_agency_description_privacy_edited": "request_agency_description_privacy_edited",
    "email_notification_sent": "email_notification_sent",
    "file_added": "file_added",
    "file_edited": "file_edited",
    "file_removed": "file_removed",
    "link_added": "link_added",
    "link_edited": "link_edited",
    "link_removed": "link_removed",
    "instructions_added": "instructions_added",
    "instructions_edited": "instructions_edited",
    "instructions_removed": "instructions_removed",
    "note_added": "note_added",
    "note_edited": "note_edited",
    "note_deleted": "note_deleted",
}

USER_TYPE = {
    "anonymous_user": "anonymous_user",
    "agency_user": "agency_user",
    "public_user": "public_user"
}

CATEGORIES = [
    ('', ''),
    ('Business', 'Business'),
    ('Civic Services', 'Civic Services'),
    ('Culture & Recreation', 'Culture & Recreation'),
    ('Education', 'Education'),
    ('Government Administration', 'Government Administration'),
    ('Environment', 'Environment'),
    ('Health', 'Health'),
    ('Housing & Development', 'Housing & Development'),
    ('Public Safety', 'Public Safety'),
    ('Social Services', 'Social Services'),
    ('Transportation', 'Transportation')
]

# direct input/mail/fax/email/phone/311/text method of answering request default is direct input
SUBMISSION_METHOD = [
    ('', ''),
    ('Direct Input', 'Direct Input'),
    ('Fax', 'Fax'),
    ('Phone', 'Phone'),
    ('Email', 'Email'),
    ('Mail', 'Mail'),
    ('In-Person', 'In-Person'),
    ('311', '311')
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

AGENCY_USER = 'Saml2In:NYC Employees'
PUBLIC_USER_NYC_ID = 'EDIRSSO'
PUBLIC_USER_FACEBOOK = 'FacebookSSO'
PUBLIC_USER_LINKEDIN = 'LinkedInSSO'
PUBLIC_USER_GOOGLE = 'GoogleSSO'
PUBLIC_USER_YAHOO = 'YahooSSO'
PUBLIC_USER_MICROSOFT = 'MSLiveSSO'
ANONYMOUS_USER = 'AnonymousUser'

PUBLIC_USER = [
    PUBLIC_USER_NYC_ID,
    PUBLIC_USER_FACEBOOK,
    PUBLIC_USER_LINKEDIN,
    PUBLIC_USER_GOOGLE,
    PUBLIC_USER_YAHOO,
    PUBLIC_USER_MICROSOFT
]

RESPONSE_TYPE = {
    "note": "note",
    "record types": "record types",
    "file": "file",
    "link": "link",
    "offline instructions": "offline instructions",
    "email": "email",
    "sms": "sms",
    "push": "push",
    "extension": "extension",
    "status": "status"
}
