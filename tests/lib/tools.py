import os
import uuid
import random

import app.lib.file_utils as fu

from itertools import product
from string import (
    ascii_lowercase,
    ascii_letters,
    digits,
)
from datetime import datetime, timedelta
from flask import current_app
from tests.lib.constants import NON_ANON_USER_GUID_LEN
from app.constants import (
    ACKNOWLEDGMENT_DAYS_DUE,
    user_type_auth,
    user_type_request,
    submission_methods,
    request_status,
)
from app.constants.response_privacy import PRIVATE
from app.constants.role_name import PUBLIC_REQUESTER
from app.models import (
    Requests,
    Files,
    Notes,
    Users,
    Agencies,
    UserRequests,
    Roles,
)
from app.request.utils import (
    generate_request_id,
    generate_guid as generate_guid_anon
)
from app.lib.date_utils import (
    get_following_date,
    get_due_date
)
from app.lib.db_utils import create_object


class RequestsFactory(object):
    """
    Helper for creating test Requests data.
    """

    filepaths = []

    def __init__(self, request_id=None, clean=True):
        """
        :param request_id: request FOIL id
        :param clean: reset data?
        """
        self.clean = clean
        date_created = datetime.utcnow()
        date_submitted = get_following_date(date_created)
        agency_ein = '0860'
        self.request = Requests(
            request_id or generate_request_id(agency_ein),
            title="I would like my vital essence.",
            description="Someone has taken my vital essence "
            "and I would like it back.",
            agency_ein=agency_ein,
            date_created=date_created,
            date_submitted=date_submitted,
            due_date=get_due_date(date_submitted,
                                  ACKNOWLEDGMENT_DAYS_DUE),
            submission=submission_methods.DIRECT_INPUT,
            status=request_status.OPEN)
        create_object(self.request)
        self.requester = Users(
            guid=generate_user_guid(user_type_auth.PUBLIC_USER_NYC_ID),
            auth_user_type=user_type_auth.PUBLIC_USER_NYC_ID,
            agency_ein=agency_ein,
            first_name='Jane',
            last_name='Doe',
            email='jdizzle@email.com',
            email_validated=True,
            terms_of_use_accepted=True,
            title='The Janest')
        create_object(self.requester)
        self.user_request = UserRequests(
            user_guid=self.requester.guid,
            auth_user_type=self.requester.auth_user_type,
            request_id=self.request.id,
            request_user_type=user_type_request.REQUESTER,
            permissions=Roles.query.filter_by(
                name=PUBLIC_REQUESTER).first().permissions)
        create_object(self.user_request)

    def add_file(self,
                 filepath=None,
                 mime_type='text/plain',
                 contents=None,
                 title=None):
        if filepath is None:
            filename = str(uuid.uuid4())
            filepath = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                    self.request.id,
                                    filename)
        else:
            filename = os.path.basename(filepath)

        self.filepaths.append(filepath)

        # create an empty file if the specified path does not exist
        if not fu.exists(filepath):
            fu.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as fp:
                fp.write(contents or
                         ''.join(random.choice(ascii_letters)
                                 for _ in range(random.randrange(100, 500))))

        response = Files(
            self.request.id,
            PRIVATE,
            title or filename,
            filename,
            mime_type,
            fu.getsize(filepath),
            fu.get_hash(filepath)
        )
        # TODO: add Events FILE_ADDED
        create_object(response)
        return response

    def add_note(self, content=None):
        response = Notes(
            self.request.id,
            PRIVATE,
            content=content or ''.join(
                random.choice(ascii_letters)
                for _ in range(random.randrange(10, 50)))
        )
        # TODO: add Events NOTE_ADDED
        create_object(response)
        return response

    def __del__(self):
        """
        Clean up time!
        - remove any files created by this factory
        - ...
        """
        if self.clean:
            for path in self.filepaths:
                if fu.exists(path):
                    fu.remove(path)


def create_user(auth_type=user_type_auth.PUBLIC_USER_NYC_ID):
    """
    :param auth_type: one of app.constants.user_type_auth
    """
    len_firstname = random.randrange(3, 8)
    len_lastname = random.randrange(3, 15)
    firstname = ''.join(random.choice(ascii_lowercase)
                        for _ in range(len_firstname)).title()
    lastname = ''.join(random.choice(ascii_lowercase)
                       for _ in range(len_lastname)).title()
    user = Users(
        guid=generate_user_guid(auth_type),
        auth_user_type=auth_type,
        agency_ein=(random.choice([ein[0] for ein in
                                  Agencies.query.with_entities(Agencies.ein).all()])
                    if auth_type == user_type_auth.AGENCY_USER
                    else None),
        first_name=firstname,
        last_name=lastname,
        email='{}{}@email.com'.format(firstname[0].lower(), lastname.lower()),
        email_validated=True,
        terms_of_use_accepted=True)
    create_object(user)
    return user


def generate_user_guid(auth_type):
    if auth_type == user_type_auth.ANONYMOUS_USER:
        return generate_guid_anon()
    else:
        return ''.join(random.choice(ascii_lowercase + digits)
                       for _ in range(NON_ANON_USER_GUID_LEN))


def create_requests_search_set(requester, other_requester):
    """
    Generate 216 unique requests.
    Every combination of title content, description content, agency description content,
    title privacy, agency description privacy, and requester is guaranteed to be unique.
    """
    agency_eins = [ein[0] for ein in
                   Agencies.query.with_entities(Agencies.ein).all()]

    for title_private, agency_desc_private, is_requester in product(range(2), repeat=3):
        for title, description, agency_description in product(("foo", "bar", "qux"), repeat=3):
            agency_ein = random.choice(agency_eins)
            date_created = get_random_date(datetime(2015, 1, 1), datetime(2016, 1, 1))
            date_submitted = get_following_date(date_created)
            request = Requests(
                generate_request_id(agency_ein),
                title=title,
                description=description,
                agency_ein=agency_ein,
                date_created=date_created,
                date_submitted=date_submitted,
                due_date=get_due_date(date_submitted,
                                      ACKNOWLEDGMENT_DAYS_DUE),
                submission=submission_methods.DIRECT_INPUT,
                status=random.choice((request_status.OPEN,
                                      request_status.CLOSED,
                                      request_status.OVERDUE,
                                      request_status.IN_PROGRESS,
                                      request_status.DUE_SOON)),
                privacy={
                    'title': bool(title_private),
                    'agency_description': bool(agency_desc_private)
                }
            )
            request.agency_description = agency_description
            create_object(request)
            user_request = UserRequests(
                user_guid=(requester.guid if is_requester
                           else other_requester.guid),
                auth_user_type=(requester.auth_user_type if is_requester
                                else other_requester.auth_user_type),
                request_id=request.id,
                request_user_type=user_type_request.REQUESTER,
                permissions=11
            )
            create_object(user_request)


def get_random_date(start, end):
    """
    :type start: datetime
    :type end: datetime
    """
    return start + timedelta(
        seconds=random.randint(
            0, int((end - start).total_seconds())
        ))
