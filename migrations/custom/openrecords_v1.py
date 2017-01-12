"""
Migrate data from OpenRecords V1 database.

"""
import json
import psycopg2
import psycopg2.extras

from datetime import datetime

from app import calendar
from app.constants import (
    request_status,
    response_privacy,
    response_type,
    determination_type,
)
from app.lib.date_utils import get_timezone_offset

DEFAULT_CATEGORY = 'All'
DUE_SOON_DAYS_THRESHOLD = 2

AGENCY_V1_NAME_TO_EIN = {
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
    # "Loft Board": "",
    "Mayor's Office of Contract Services": "002H",
    "Mayor's Office of Media and Entertainment": "002M",
    "New York City Fire Department": "0057",
    "New York City Housing Authority": "0996",
    # "New York City Housing Development Corporation": "",
    "NYC Emergency Management": "0017",  # NYC Offic of Emergency Management
    "Office of Administrative Trials and Hearings": "0820",
    # "Office of Collective Bargaining": "",
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
    # "Procurement Policy Board": "",
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


def transfer_request(row_v1, cur_v1, cur_v2):
    cur_v1.execute("SELECT name FROM department WHERE id = %s" % row_v1.department_id)

    agency_ein = AGENCY_V1_NAME_TO_EIN[cur_v1.fetchone().name]

    privacy = {
        "title": bool(row_v1.title_private),
        "agency_description": True  # row_v1.description_private NOT USED  # FIXME: some should be public by now
    }

    query = ("INSERT INTO requests ("
             "id,"
             "agency_ein,"
             "category,"
             "title,"
             "description,"
             "date_created,"
             "date_submitted,"
             "due_date,"
             "submission,"
             "status,"
             "privacy,"
             "agency_description,"
             "agency_description_release_date)"
             "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    cur_v2.execute(query, (
        row_v1.id,                          # id
        agency_ein,                         # agency id
        DEFAULT_CATEGORY,                   # category
        row_v1.summary,                     # title
        row_v1.text,                        # description
        row_v1.date_created,                # date_created
        row_v1.date_received,               # date_submitted
        row_v1.due_date,                    # due_date
        row_v1.offline_submission_type,     # submission
        _get_compatible_status(row_v1),      # status
        json.dumps(privacy),                # privacy
        row_v1.agency_description,          # agency_description
        row_v1.agency_description_due_date  # agency_description_release_date
    ))


def _get_compatible_status(row):
    if row.status in [request_status.CLOSED, request_status.OPEN]:
        status = row.status
    else:
        now = datetime.now()
        due_soon_date = calendar.addbusdays(
            now, DUE_SOON_DAYS_THRESHOLD
        ).replace(hour=23, minute=59, second=59)  # the entire day
        if now > row.due_date:
            status = request_status.OVERDUE
        elif due_soon_date >= row.due_date:
            status = request_status.DUE_SOON
        else:
            status = request_status.IN_PROGRESS
    return status


def _create_response(child, type_, cur_v2, conn_v2, privacy=None, date_created=None):
    query = ("INSERT INTO responses ("
             "request_id,"
             "privacy,"
             "date_modified,"
             "deleted,"
             "type,"
             "is_editable)"
             "VALUES (%s, %s, %s, %s, %s, %s)")

    if date_created is None:
        date_created = child.date_created

    date_created_utc = date_created - get_timezone_offset(date_created, 'America/New_York')

    cur_v2.execute(query, (
        child.request_id,                      # request_id
        privacy or PRIVACY[child.privacy],     # privacy
        date_created_utc,                      # date_modified # offset
        False,                                 # deleted
        type_,                                 # type
        True                                   # is_editable
    ))

    conn_v2.commit()

    cur_v2.execute("SELECT LASTVAL()")
    return cur_v2.fetchone().lastval


def transfer_notes(cur_v1, cur_v2, conn_v2):
    cur_v1.execute("SELECT * FROM note WHERE text NOT LIKE '%Request extended:%' AND text NOT LIKE '{%}'")

    for note in cur_v1.fetchall():

        response_id = _create_response(note, response_type.NOTE, cur_v2, conn_v2)

        query = ("INSERT INTO notes ("
                 "id,"
                 "content)"
                 "VALUES (%s, %s)")

        cur_v2.execute(query, (
            response_id,    # id
            note.text       # content
        ))

        conn_v2.commit()


def transfer_denials(cur_v1, cur_v2, conn_v2):
    cur_v1.execute("SELECT * FROM note WHERE text LIKE '{%is denied%'")

    for note in cur_v1.fetchall():

        response_id = _create_response(note, response_type.DETERMINATION, cur_v2, conn_v2,
                                       privacy=response_privacy.RELEASE_AND_PUBLIC)

        query = ("INSERT INTO determinations ("
                 "id,"
                 "dtype,"
                 "reason)"
                 "VALUES (%s, %s, %s)")

        cur_v2.execute(query, (
            response_id,
            determination_type.DENIAL,
            note.text.lstrip('{"').rstrip('"}').replace('","', '|')
        ))

        conn_v2.commit()


def transfer_closings(cur_v1, cur_v2, conn_v2):
    cur_v1.execute("SELECT * FROM note WHERE text LIKE '{%}' and text NOT LIKE '%denied%'")

    for note in cur_v1.fetchall():

        response_id = _create_response(note, response_type.DETERMINATION, cur_v2, conn_v2,
                                       privacy=response_privacy.RELEASE_AND_PUBLIC)

        query = ("INSERT INTO determinations ("
                 "id,"
                 "dtype,"
                 "reason)"
                 "VALUES (%s, %s, %s)")

        reason = note.text.lstrip('{"').rstrip('"}').replace('","', '|')
        if reason == '':
            reason = 'No reasons for closing provided.'

        cur_v2.execute(query, (
            response_id,
            determination_type.CLOSING,
            reason
        ))

        conn_v2.commit()


def transfer_acknowledgments(cur_v1, cur_v2, conn_v2):
    cur_v1.execute("SELECT * FROM email_notification WHERE subject LIKE '%Acknowledged%'")

    for email in cur_v1.fetchall():

        response_id = _create_response(email, response_type.DETERMINATION, cur_v2, conn_v2,
                                       privacy=response_privacy.RELEASE_AND_PUBLIC,
                                       date_created=email.time_sent)

        query = ("INSERT INTO determinations ("
                 "id,"
                 "dtype,"
                 # "reason,"  # TODO: fetch reason from email content or leave null
                 "date)"
                 "VALUES (%s, %s, %s)")

        cur_v1.execute("SELECT date_received FROM request WHERE id = '%s'" % email.request_id)
        date = calendar.addbusdays(
            cur_v1.fetchone().date_received,
            5 + int(email.email_content['acknowledge_status'].rstrip(" days"))  # TODO: verify days to add
        )

        cur_v2.execute(query, (
            response_id,
            determination_type.ACKNOWLEDGMENT,
            date
        ))


def transfer_reopenings(cur_v1, cur_v2, conn_v2):
    cur_v1.execute("SELECT * FROM email_notification WHERE subject LIKE '%reopened%'")

    for email in cur_v1.fetchall():

        response_id = _create_response(email, response_type.DETERMINATION, cur_v2, conn_v2,
                                       privacy=response_privacy.RELEASE_AND_PUBLIC,
                                       date_created=email.time_sent)

        query = ("INSERT INTO determinations ("
                 "id,"
                 "dtype,"
                 "date)"
                 "VALUES (%s, %s, %s)")

        date = datetime.now()  # FIXME: date should be the due_date at the time of reopening

        cur_v2.execute(query, (
            response_id,
            determination_type.ACKNOWLEDGMENT,
            date
        ))


def transfer_all(cur_v1, cur_v2, conn_v2):
    # Requests
    cur_v1.execute("SELECT * FROM request")
    for row in cur_v1.fetchall():
        transfer_request(row, cur_v1, cur_v2)
    conn_v2.commit()

    # Responses
    transfer_notes(cur_v1, cur_v2, conn_v2)
    # Responses: Determinations
    transfer_denials(cur_v1, cur_v2, conn_v2)
    transfer_closings(cur_v1, cur_v2, conn_v2)
    transfer_acknowledgments(cur_v1, cur_v2, conn_v2)
    transfer_reopenings(cur_v1, cur_v2, conn_v2)
    # TODO: transfer_extensions()


def main():
    conn_v1 = psycopg2.connect(database="openrecords_v1", user="vagrant")
    conn_v2 = psycopg2.connect(database="openrecords_v2_0_dev", user="vagrant")
    cur_v1 = conn_v1.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
    cur_v2 = conn_v2.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)

    # transfer_all(cur_v1, cur_v2, conn_v2)

    transfer_reopenings(cur_v1, cur_v2, conn_v2)


if __name__ == "__main__":
    main()
