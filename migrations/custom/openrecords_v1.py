"""
Migrate data from OpenRecords V1 database.

"""
import json
import psycopg2
import psycopg2.extras
# from docopt import docopt

AGENCY_CODES = {
    "City Commission on Human Rights": 228,  # 226 Human Rights Commission
    "Department of Education": 40,  #
    "Department of Information Technology and Telecommunications": 858,
    "Department of Records and Information Services": 860,
    "Office of the Mayor": 2,
    "Office of Administrative Trials and Hearings": 820,  # ??? 249 requests exists with this id
    "Office of the Chief Medical Examiner": 816,
    "NYC Emergency Management": 17,
    "Equal Employment Practices Commission": 133,
    "Commission to Combat Police Corruption": 32,
    "Department for the Aging": 125,
    "Office of Payroll Administration": 131,
    "Department of Parks and Recreation": 846,
    "Business Integrity Commission": 831,
    "Department of Youth and Community Development": 260,
    "Department of Sanitation": 827,
    "Board of Correction": 73,
    "Department of Cultural Affairs": 126,
    "Department of Design and Construction": 850,

    None: 0
}

STATUSES = {
    'OPEN': 'Open',
    'IN PROGRESS': 'In Progress',
    'DUE SOON': 'Due Soon',
    'OVERDUE': 'Overdue',
    'CLOSED': 'Closed',
    'REOPENED': 'Re-Opened',
    'RE-OPENED': 'Re-Opened',
}

# Other observed statuses (defaulted to 'In Progress')
#   A response has been added.
#   Rerouted
#   XX days


def transfer_row(row_v1, cur_v1, cur_v2):
    cur_v1.execute("SELECT name FROM department WHERE id = %s" % row_v1.department_id)
    agency_ein = AGENCY_CODES[cur_v1.fetchone().name]
    if agency_ein != 820:  # does not exist?
        if agency_ein == 228:
            agency_ein = 226

        status = STATUSES.get(row_v1.status.strip().upper(), 'In Progress')

        privacy = {
            "title": bool(row_v1.title_private),
            "agency_description": True  # row_v1.description_private NOT USED
        }

        query = ("INSERT INTO requests ("
                 "id,"
                 "agency_ein,"
                 "title,"
                 "description,"
                 "date_created,"
                 "date_submitted,"
                 "due_date,"
                 "submission,"  # FIXME: not nullable
                 "status,"
                 "privacy,"
                 "agency_description)"
                 "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

        cur_v2.execute(query, (
            row_v1.id,  # id
            agency_ein,  # agency id
            row_v1.summary,  # title
            row_v1.text,  # description
            row_v1.date_created,  # date_created
            row_v1.date_received,  # date_submitted
            row_v1.due_date,  # due_date
            row_v1.offline_submission_type,  # submission
            status,  # status
            json.dumps(privacy),  # privacy
            row_v1.agency_description  # agency_description
            # FIXME: agency_description_due_date missing
        ))


def main():
    conn_v1 = psycopg2.connect(database="openrecords_v1", user="vagrant")
    conn_v2 = psycopg2.connect(database="openrecords_v2_0_dev", user="vagrant")
    cur_v1 = conn_v1.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
    cur_v2 = conn_v2.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)

    cur_v1.execute("SELECT * FROM request")
    for row in cur_v1.fetchall():
        transfer_row(row, cur_v1, cur_v2)
    conn_v2.commit()


if __name__ == "__main__":
    main()
