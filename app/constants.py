ACKNOWLEDGEMENT_DAYS_DUE = 5
UPLOAD_FOLDER = '/csv/upload'
ALLOWED_EXTENSIONS = set(['txt', 'csv'])

event_type = {
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

# FOR TESTING
agencies = [
    ('', ''),
    ('Agency1', 'Agency1'),
    ('Agency2', 'Agency2'),
    ('Agency3', 'Agency3'),
    ('Agency4', 'Agency4'),
    ('Agency5', 'Agency5'),
    ('Agency6', 'Agency6'),
    ('Agency7', 'Agency7'),
    ('Agency8', 'Agency8')
]

categories = [
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
submission_method = [
    ('', ''),
    ('Direct Input', 'Direct Input'),
    ('Fax', 'Fax'),
    ('Phone', 'Phone'),
    ('Email', 'Email'),
    ('Mail', 'Mail'),
    ('In-Person', 'In-Person'),
    ('311', '311')
]
