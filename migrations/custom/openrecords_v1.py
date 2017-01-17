"""
Migrate data from OpenRecords V1 database.

Usage:
    PYTHONPATH=/.../openrecords_v2_0 python migrations/custom/openrecords_v1.py

"""
import math
import json
import psycopg2.extras

from functools import wraps
from datetime import datetime

from nameparser import HumanName

from app import calendar
from app.constants import (
    request_status,
    response_privacy,
    response_type,
    determination_type,
    role_name,
    user_type_auth,
    ACKNOWLEDGMENT_DAYS_DUE,
)
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.lib.user_information import create_mailing_address
from app.request.utils import generate_guid
from app.lib.date_utils import (
    get_timezone_offset,
    get_due_date,
    process_due_date,
)

try:
    import progressbar
    SHOW_PROGRESSBAR = True
except ImportError:
    SHOW_PROGRESSBAR = False


CONN_V1 = psycopg2.connect(database="openrecords_v1", user="vagrant")
CONN_V2 = psycopg2.connect(database="openrecords_v2_0_dev", user="vagrant")
CUR_V1_X = CONN_V1.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
CUR_V1 = CONN_V1.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
CUR_V2 = CONN_V2.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)

CHUNKSIZE = 500
DEFAULT_CATEGORY = 'All'
DUE_SOON_DAYS_THRESHOLD = 2
TZ_NY = 'America/New_York'

AGENCY_V1_NAME_TO_EIN = {
    # None = no ein yet found
    "Administration for Children's Services": "0067",
    "Board of Correction": "0073",
    "Board of Elections": "0003",
    "Board of Standards and Appeals": "0059",
    "Business Integrity Commission": "0831",
    "City Commission on Human Rights": "0226",
    "Civilian Complaint Review Board": "0054",
    "Civil Service Commission": "0134",
    "Commission to Combat Police Corruption": "032A",
    "Conflicts of Interest Board": "0312",
    "Department for the Aging": "0125",
    "Department of Buildings": "0810",
    "Department of City Planning": "0030",
    "Department of Citywide Administrative Services": "0868",
    "Department of Consumer Affairs": "0866",
    "Department of Correction": "0072",
    "Department of Cultural Affairs": "0126",
    "Department of Design and Construction": "0850",
    "Department of Education": "0040",
    "Department of Environmental Protection": "0826",
    "Department of Finance": "0836",
    "Department of Health and Mental Hygiene": "0816",
    "Department of Homeless Services": "0071",
    "Department of Housing Preservation and Development": "0806",
    "Department of Information Technology and Telecommunications": "0858",
    "Department of Investigation": "0032",
    "Department of Parks and Recreation": "0846",
    "Department of Probation": "0781",
    "Department of Records and Information Services": "0860",
    "Department of Sanitation": "0827",
    "Department of Transportation": "0841",
    "Department of Youth and Community Development": "0260",
    "Design Commission": "002A",
    "Equal Employment Practices Commission": "0113",
    "Financial Information Services Agency": "0127",
    "Housing Recovery Operations": "826A",
    "Human Resources Administration": "0069",
    "Landmarks Preservation Commission": "0136",
    "Law Department": "0025",
    "Loft Board": None,
    "Mayor's Office of Contract Services": "002H",
    "Mayor's Office of Media and Entertainment": "002M",
    "New York City Fire Department": "0057",
    "New York City Housing Authority": "0996",
    "New York City Housing Development Corporation": None,
    "NYC Emergency Management": "0017",  # NYC Office of Emergency Management
    "Office of Administrative Trials and Hearings": "0820",
    "Office of Collective Bargaining": None,
    "Office of Environmental Remediation": "002K",  # Mayor's Office of Environmental Remediation
    "Office of Labor Relations": "0214",  # NYC Office of Labor Relations
    "Office of Long-Term Planning and Sustainability": "002T",
    "Office of Management and Budget": "0019",
    "Office of Payroll Administration": "0131",
    "Office of the Actuary": "0008",  # NYC Office of the Actuary
    "Office of the Chief Medical Examiner": "816A",  # NYC Office of the Chief Medical Examiner
    "Office of the Mayor": "0002",  # Mayor's Office
    "Office of the Special Narcotics Prosecutor": "0906",  # NYC Office of the Special Narcotics Prosecutor
    "Police Department": "0056",
    "Procurement Policy Board": None,
    "School Construction Authority": "0044",
    "Small Business Services": "0801",  # Department of Small Business Services
    "Taxi and Limousine Commission": "0156",
}

PRIVACY = [
    None,
    response_privacy.PRIVATE,
    response_privacy.RELEASE_AND_PRIVATE,
    response_privacy.RELEASE_AND_PUBLIC
]


class MockProgressBar(object):
    """ Mock progressbar.ProgressBar """

    def __init__(self, max_value):
        self.max = max_value

    def update(self, num):
        pass

    def finish(self):
        print(self.max, end='')


def setup_transfer(tablename, query):
    def decorator(transfer_func):
        @wraps(transfer_func)
        def wrapped():
            CUR_V1_X.execute(query)
            bar = progressbar.ProgressBar if SHOW_PROGRESSBAR else MockProgressBar
            bar = bar(max_value=CUR_V1_X.rowcount)
            print(tablename + "...")
            for chunk in range(math.ceil(CUR_V1_X.rowcount / CHUNKSIZE)):
                for i, row in enumerate(CUR_V1_X.fetchmany(CHUNKSIZE)):
                    transfer_func(row)
                    bar.update(i + 1 + (chunk * CHUNKSIZE))
                CONN_V2.commit()
            bar.finish()
            print()
        return wrapped
    return decorator


def _get_compatible_status(request):
    if request.status in [request_status.CLOSED, request_status.OPEN]:
        status = request.status
    else:
        now = datetime.now()
        due_soon_date = calendar.addbusdays(
            now, DUE_SOON_DAYS_THRESHOLD
        ).replace(hour=23, minute=59, second=59)  # the entire day
        if now > request.due_date:
            status = request_status.OVERDUE
        elif due_soon_date >= request.due_date:
            status = request_status.DUE_SOON
        else:
            status = request_status.IN_PROGRESS
    return status


@setup_transfer("Requests", "SELECT * FROM request")
def transfer_requests(request):
    CUR_V1.execute("SELECT name FROM department WHERE id = %s" % request.department_id)

    agency_ein = AGENCY_V1_NAME_TO_EIN[CUR_V1.fetchone().name]

    privacy = {
        "title": bool(request.title_private),
        "agency_description": True  # row_v1.description_private NOT USED  # FIXME: some should be public by now
    }

    query = ("INSERT INTO requests ("
             "id, "
             "agency_ein, "
             "category, "
             "title, "
             "description, "
             "date_created, "
             "date_submitted, "
             "due_date, "
             "submission, "
             "status, "
             "privacy, "
             "agency_description, "
             "agency_description_release_date) "
             "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    CUR_V2.execute(query, (
        request.id,                             # id
        agency_ein,                             # agency id
        DEFAULT_CATEGORY,                       # category
        request.summary,                        # title
        request.text,                           # description
        request.date_created,                   # date_created
        request.date_received,                  # date_submitted
        request.due_date,                       # due_date
        request.offline_submission_type,        # submission
        _get_compatible_status(request),        # status
        json.dumps(privacy),                    # privacy
        request.agency_description,             # agency_description
        request.agency_description_due_date     # agency_description_release_date
    ))


def _create_response(child, type_, release_date, privacy=None, date_created=None):
    query = ("INSERT INTO responses ("
             "request_id, "
             "privacy, "
             "date_modified, "
             "release_date, "
             "deleted, "
             '"type", '
             "is_editable) "
             "VALUES (%s, %s, %s, %s, %s, %s, %s)")

    if date_created is None:
        date_created = child.date_created

    date_created_utc = date_created - get_timezone_offset(date_created, TZ_NY)

    CUR_V2.execute(query, (
        child.request_id,                      # request_id
        privacy or PRIVACY[child.privacy],     # privacy
        date_created_utc,                      # date_modified
        release_date,                          # release_date
        False,                                 # deleted
        type_,                                 # type
        True                                   # is_editable
    ))

    CONN_V2.commit()

    CUR_V2.execute("SELECT LASTVAL()")
    return CUR_V2.fetchone().lastval


def _get_note_release_date(note):
    if PRIVACY[note.privacy] == response_privacy.RELEASE_AND_PUBLIC:
        release_date = calendar.addbusdays(note.date_created, RELEASE_PUBLIC_DAYS)
        return release_date - get_timezone_offset(release_date, TZ_NY)
    return None


@setup_transfer("Notes", "SELECT * FROM note WHERE text NOT LIKE '%Request extended:%' AND text NOT LIKE '{%}'")
def transfer_notes(note):
    response_id = _create_response(note, response_type.NOTE,
                                   _get_note_release_date(note))

    query = ("INSERT INTO notes ("
             "id, "
             "content) "
             "VALUES (%s, %s)")

    CUR_V2.execute(query, (
        response_id,    # id
        note.text       # content
    ))


@setup_transfer("Denials", "SELECT * FROM note WHERE text LIKE '{%is denied%'")
def transfer_denials(note):
    response_id = _create_response(note, response_type.DETERMINATION,
                                   _get_note_release_date(note),
                                   privacy=response_privacy.RELEASE_AND_PUBLIC)

    query = ("INSERT INTO determinations ("
             "id, "
             "dtype, "
             "reason) "
             "VALUES (%s, %s, %s)")

    CUR_V2.execute(query, (
        response_id,
        determination_type.DENIAL,
        note.text.lstrip('{"').rstrip('"}').replace('","', '|')
    ))


@setup_transfer("Closings", "SELECT * FROM note WHERE text LIKE '{%}' and text NOT LIKE '%denied%'")
def transfer_closings(note):
    response_id = _create_response(note, response_type.DETERMINATION,
                                   _get_note_release_date(note),
                                   privacy=response_privacy.RELEASE_AND_PUBLIC)

    query = ("INSERT INTO determinations ("
             "id, "
             "dtype, "
             "reason) "
             "VALUES (%s, %s, %s)")

    reason = note.text.lstrip('{"').rstrip('"}').replace('","', '|')
    if reason == '':
        reason = 'No reasons for closing provided.'

    CUR_V2.execute(query, (
        response_id,
        determination_type.CLOSING,
        reason
    ))


def _get_email_release_date(email):
    release_date = calendar.addbusdays(email.time_sent, RELEASE_PUBLIC_DAYS)
    return release_date - get_timezone_offset(release_date, TZ_NY)


@setup_transfer("Acknowledgments", "SELECT * FROM email_notification WHERE subject LIKE '%Acknowledged%'")
def transfer_acknowledgments(email):
    response_id = _create_response(email, response_type.DETERMINATION,
                                   _get_email_release_date(email),
                                   privacy=response_privacy.RELEASE_AND_PUBLIC,
                                   date_created=email.time_sent)

    query = ("INSERT INTO determinations ("
             "id, "
             "dtype, "
             '"date") '
             "VALUES (%s, %s, %s)")

    CUR_V1.execute("SELECT date_received FROM request WHERE id = '%s'" % email.request_id)
    date = get_due_date(
        CUR_V1.fetchone().date_received,
        ACKNOWLEDGMENT_DAYS_DUE + int(email.email_content['acknowledge_status'].rstrip(" days")),
        TZ_NY
    )
    CUR_V2.execute(query, (
        response_id,
        determination_type.ACKNOWLEDGMENT,
        date
    ))


@setup_transfer("Re-Openings", "SELECT * FROM email_notification WHERE subject LIKE '%reopened%'")
def transfer_reopenings(email):
    response_id = _create_response(email, response_type.DETERMINATION,
                                   _get_email_release_date(email),
                                   privacy=response_privacy.RELEASE_AND_PUBLIC,
                                   date_created=email.time_sent)

    query = ("INSERT INTO determinations ("
             "id, "
             "dtype, "
             '"date") '
             "VALUES (%s, %s, %s)")

    CUR_V1.execute("SELECT due_date FROM request WHERE id = '%s'" % email.request_id)
    due_date = CUR_V1.fetchone().due_date
    date = due_date - get_timezone_offset(due_date, TZ_NY)

    CUR_V2.execute(query, (
        response_id,
        determination_type.ACKNOWLEDGMENT,
        date
    ))


@setup_transfer('Extensions', "SELECT * FROM email_notification WHERE subject LIKE '%Extension%'")
def transfer_extensions(email):
    response_id = _create_response(email, response_type.DETERMINATION,
                                   _get_email_release_date(email),
                                   privacy=response_privacy.RELEASE_AND_PUBLIC,
                                   date_created=email.time_sent)

    query = ("INSERT INTO determinations ("
             "id, "
             "dtype, "
             "reason, "
             '"date") '
             "VALUES (%s, %s, %s, %s)")

    # FIXME: how do we handle multiple extensions? request.prev_status might help...
    date = email.email_content['due_date']
    if email.email_content['days_after'] == -1:  # if custom
        date = datetime.strptime(date, '%m/%d/%Y')
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    date = process_due_date(date, TZ_NY)

    CUR_V2.execute(query, (
        response_id,
        determination_type.EXTENSION,
        date
    ))


def _get_record_release_date(record):
    if PRIVACY[record.privacy] == response_privacy.RELEASE_AND_PUBLIC:
        if record.release_date is not None:
            release_date = record.release_date
        else:
            release_date = calendar.addbusdays(record.date_created, RELEASE_PUBLIC_DAYS)
        return release_date - get_timezone_offset(release_date, TZ_NY)
    return None


@setup_transfer('Files', "SELECT * FROM record WHERE filename IS NOT NULL AND filename != ''")
def transfer_files(record):
    response_id = _create_response(record, response_type.FILE,
                                   _get_record_release_date(record))

    # TODO: in script that transfers files, update files table (mime type, size, hash)
    query = ("INSERT INTO files ("
             "id, "
             "title, "
             '"name") '
             "VALUES (%s, %s, %s)")

    if record.description is None or record.description.strip() == '':
        title = record.filename
    else:
        title = record.description

    CUR_V2.execute(query, (
        response_id,
        title,
        record.filename
    ))


@setup_transfer('Links', "SELECT * FROM record WHERE url IS NOT NULL and url != '1'")
def transfer_links(record):
    response_id = _create_response(record, response_type.LINK,
                                   _get_record_release_date(record))

    query = ("INSERT INTO links ("
             "id, "
             "title, "
             "url) "
             "VALUES (%s, %s, %s)")

    CUR_V2.execute(query, (
        response_id,
        record.description,
        record.url
    ))


@setup_transfer('Instructions', "SELECT * FROM record WHERE access IS NOT NULL")
def transfer_instructions(record):
    response_id = _create_response(record, response_type.INSTRUCTIONS,
                                   _get_record_release_date(record))

    query = ("INSERT INTO instructions ("
             "id, "
             "content) "
             "VALUES (%s, %s)")

    if record.description is None or record.description.strip() == '':
        content = record.access
    else:
        content = ':\n\n'.join((record.description, record.access))

    CUR_V2.execute(query, (
        response_id,
        content
    ))


@setup_transfer('Emails', "SELECT * FROM email_notification")
def transfer_emails(email):
    response_id = _create_response(email, response_type.EMAIL,
                                   _get_email_release_date(email),
                                   privacy=response_privacy.PRIVATE,
                                   date_created=email.time_sent)

    query = ("INSERT INTO emails ("
             "id, "
             '"to", '
             "subject, "
             "body) "
             "VALUES (%s, %s, %s, %s)")

    CUR_V1.execute("SELECT email FROM public.user WHERE id = %s"
                   % email.recipient)
    to = CUR_V1.fetchone().email

    # FIXME: subject like '%assigned%' or subject like '%Submitted%'; does not have email_text, find body

    CUR_V2.execute(query, (
        response_id,
        to,
        email.subject,
        email.email_content['email_text']
    ))


@setup_transfer('Users', "SELECT * FROM public.user "
                         "WHERE alias NOT IN (SELECT name FROM department) "
                         "AND alias IS NOT NULL "
                         "OR (first_name IS NOT NULL AND last_name IS NOT NULL)")
def transfer_users(user):
    # get agency_ein and auth_user_type
    auth_user_type = user_type_auth.AGENCY_LDAP_USER
    if user.department_id:
        CUR_V1.execute("SELECT name FROM department WHERE id = %s" % user.department_id)
        agency_ein = AGENCY_V1_NAME_TO_EIN[CUR_V1.fetchone().name]
    else:
        agency_ein = None
        auth_user_type = user_type_auth.ANONYMOUS_USER

    mailing_address = create_mailing_address(
        user.address1,
        user.city,
        user.state,
        user.zipcode,
        user.address2
    )

    name = HumanName(user.alias)  # alias assumed never none

    query = ("INSERT INTO users ("
             "guid, "
             "auth_user_type, "
             "agency_ein, "
             "is_super, "
             "is_agency_active, "
             "is_agency_admin, "
             "first_name, "
             "middle_initial, "
             "last_name, "
             "email, "
             "email_validated, "
             "terms_of_use_accepted, "
             "title, "
             "organization, "
             "phone_number, "
             "fax_number, "
             "mailing_address) "
             "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    CUR_V2.execute(query, (
        generate_guid(),                                    # guid
        auth_user_type,                                     # auth_user_type
        agency_ein,                                         # agency_ein
        False,                                              # is_super
        user.is_staff,                                      # is_agency_active
        user.role == role_name.AGENCY_ADMIN,                # is_agency_admin
        name.first.title().strip(),                         # first_name
        name.middle[0].upper() if name.middle else None,    # middle_initial
        name.last.title().strip(),                          # last_name
        user.email,                                         # email
        False,                                              # email_validated
        False,                                              # terms_of_user_accepted
        None,                                               # title
        None,                                               # organization
        user.phone if user.phone != 'None' else None,       # phone_number
        user.fax if user.fax != 'None' else None,           # fax_number
        json.dumps(mailing_address)                         # mailing_address
    ))


def transfer_all():
    transfer_requests()
    transfer_users()
    # transfer_user_requests()

    # Responses
    transfer_notes()
    transfer_files()
    transfer_links()
    transfer_instructions()
    # Responses: Determinations
    transfer_denials()
    transfer_closings()
    transfer_acknowledgments()
    transfer_reopenings()
    # TODO: transfer_extensions()


if __name__ == "__main__":
    transfer_users()
