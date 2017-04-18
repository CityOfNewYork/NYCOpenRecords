import os
from operator import ior
from functools import reduce
from datetime import datetime, timedelta
from flask import current_app
from app import calendar
from app.models import (
    Users,
    Roles,
    Requests,
    Agencies,
    Events,
    Responses,
    UserRequests,
)
from app.constants import (
    permission,
    role_name,
    event_type,
    user_type_auth,
    user_type_request,
    request_status,
    response_privacy,
    submission_methods,
    determination_type,
    ACKNOWLEDGMENT_DAYS_DUE,
)
from app.lib.date_utils import (
    local_to_utc,
    utc_to_local,
    get_due_date,
    process_due_date,
    get_following_date,
)
from app.response.utils import format_determination_reasons
from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    UserFactory,
    RequestFactory,
    TestHelpers
)
from tests.lib.constants import SCREAM_FILE


class UserFactoryTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.uf = UserFactory()
        self.agency_ein = Agencies.query.first().ein

    def test_create_user(self):
        auth_type = user_type_auth.PUBLIC_USER_NYC_ID

        # user 1 (default kwargs)
        u1 = self.uf.create_user(auth_type)

        # user 2
        email = "shrimp@mail.com"
        first_name = "Bubba"
        last_name = "Gump"
        title = "Prawn Meister"
        organization = "Mail-Order Shrimp Inc."
        phone_number = "(123) 456-7890"
        fax_number = "(098) 765-4321"
        mailing_address = {
            "address_one": "P. Sherman 42 Wallaby Way",
            "address_two": "Apt. B",
            "city": "Sydney",
            "state": "Australia",  # oh yeah
            "zip": "10101"
        }
        email_validated = False
        terms_of_use_accepted = False
        u2 = self.uf.create_user(
            auth_type,
            email=email,
            first_name=first_name,
            last_name=last_name,
            title=title,
            organization=organization,
            phone_number=phone_number,
            fax_number=fax_number,
            mailing_address=mailing_address,
            email_validated=email_validated,
            terms_of_use_accepted=terms_of_use_accepted
        )

        # user 1
        self.__assert_user_data_correct(
            u1,
            auth_type,
            agency_ein=None,
            email_validated=True,
            terms_of_use_accepted=True,
            fuzzy=True)

        # user 2
        self.__assert_user_data_correct(
            u2,
            auth_type,
            agency_ein=None,
            email_validated=email_validated,
            terms_of_use_accepted=terms_of_use_accepted,
            email=email,
            first_name=first_name,
            last_name=last_name,
            title=title,
            organization=organization,
            phone_number=phone_number,
            fax_number=fax_number,
            mailing_address=mailing_address)

    def test_create_user_wrong_agency_attributes(self):

        with self.assertRaises(AssertionError):
            self.uf.create_user(user_type_auth.AGENCY_USER)

        with self.assertRaises(AssertionError):
            self.uf.create_user(user_type_auth.ANONYMOUS_USER, agency_ein=self.agency_ein)

        with self.assertRaises(AssertionError):
            self.uf.create_user(user_type_auth.ANONYMOUS_USER, is_agency_active=True)

        with self.assertRaises(AssertionError):
            self.uf.create_user(user_type_auth.ANONYMOUS_USER, is_agency_admin=True)

    def test_create_anonymous_user(self):
        user = self.uf.create_anonymous_user()
        self.__assert_user_data_correct(
            user,
            user_type_auth.ANONYMOUS_USER,
            agency_ein=None,
            email_validated=False,
            terms_of_use_accepted=False,
            fuzzy=True
        )

    def test_create_agency_user(self):
        u1 = self.uf.create_agency_user()
        u2 = self.uf.create_agency_user(self.agency_ein, is_agency_active=True, is_agency_admin=True)

        # user 1
        self.assertTrue(u1.agency_ein in (a[0] for a in Agencies.query.with_entities(Agencies.ein).all()))
        self.__assert_user_data_correct(
            u1,
            user_type_auth.AGENCY_USER,
            agency_ein=u1.agency_ein,
            email_validated=True,
            terms_of_use_accepted=True,
            fuzzy=True
        )

        # user 2
        self.__assert_user_data_correct(
            u2,
            user_type_auth.AGENCY_USER,
            agency_ein=self.agency_ein,
            email_validated=True,
            terms_of_use_accepted=True,
            fuzzy=True,
            is_agency_admin=True,
            is_agency_active=True,
        )

    def test_create_public_user(self):
        user = self.uf.create_public_user()
        self.assertTrue(user.auth_user_type in user_type_auth.PUBLIC_USER_TYPES)
        self.__assert_user_data_correct(
            user,
            user.auth_user_type,
            agency_ein=None,
            email_validated=True,
            terms_of_use_accepted=True,
            fuzzy=True
        )

    def __assert_user_data_correct(self,
                                   user,
                                   auth_type,
                                   agency_ein,
                                   email_validated,
                                   terms_of_use_accepted,
                                   fuzzy=False,
                                   email=None,
                                   first_name=None,
                                   last_name=None,
                                   title=None,
                                   organization=None,
                                   phone_number=None,
                                   fax_number=None,
                                   mailing_address=None,
                                   is_agency_active=False,
                                   is_agency_admin=False):
        """
        Retrieves Users database records and compares its data to the supplied argument value.
        If fuzzy is True, only types are checked for the user-specific kwargs.
        """
        user = Users.query.get((user.guid, user.auth_user_type))
        user_list = [
            user.auth_user_type,
            user.agency_ein,
            user.email_validated,
            user.terms_of_use_accepted,
            user.is_agency_active,
            user.is_agency_admin,
        ]
        check_list = [
            auth_type,
            agency_ein,
            email_validated,
            terms_of_use_accepted,
            is_agency_active,
            is_agency_admin,
        ]
        if fuzzy:
            user_list += [
                type(user.email),
                type(user.first_name),
                type(user.last_name),
                type(user.title),
                type(user.organization),
                type(user.phone_number),
                type(user.fax_number),
                type(user.mailing_address),
            ]
            check_list += [
                str,  # email
                str,  # first name
                str,  # last name
                str,  # title
                str,  # organization
                str,  # phone_number
                str,  # fax_number
                dict,  # mailing_address
            ]
        else:
            user_list += [
                user.email,
                user.first_name,
                user.last_name,
                user.title,
                user.organization,
                user.phone_number,
                user.fax_number,
                user.mailing_address,
            ]
            check_list += [
                email,
                first_name,
                last_name,
                title,
                organization,
                phone_number,
                fax_number,
                mailing_address,
            ]

        self.assertEqual(user_list, check_list)


class RequestFactoryTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.agency_ein_860 = "0860"
        self.parent_ein_860 = "860"
        self.agency_ein_002 = "0002"
        uf = UserFactory()
        self.user_860 = uf.create_agency_user(self.agency_ein_860)
        self.admin_860 = uf.create_agency_admin(self.agency_ein_860)
        self.rf = RequestFactory()
        self.rf_agency_860 = RequestFactory(agency_ein=self.agency_ein_860)
        self.rf_agency_002 = RequestFactory(agency_ein=self.agency_ein_002)
        self.tz_name = current_app.config["APP_TIMEZONE"]

    def test_create_request_default(self):
        request = self.rf.create_request(self.user_860)
        self.__assert_request_data_correct(
            self.user_860,
            request,
            self.parent_ein_860,
            default=True,
        )
        # check associated users
        requester = Users.query.filter_by(auth_user_type=user_type_auth.ANONYMOUS_USER).one()
        self.assertEqual(request.requester, requester)
        self.assertFalse(self.user_860 in request.agency_users)
        self.assertTrue(self.admin_860 in request.agency_users)

    def test_create_request_custom(self):
        title = "Where did all the fish go?"
        description = "I demand to know where all of my fish ran off to."
        agency_description = "Inquiry into the disappearance local marine life."
        category = "Fishies"
        title_privacy = False
        ag_privacy = False
        submission = submission_methods.IN_PERSON
        status = request_status.IN_PROGRESS
        date_created = datetime.utcnow()
        due_date = date_created + timedelta(days=90)
        request = self.rf.create_request(
            self.user_860,
            title,
            description,
            agency_description,
            self.user_860.agency_ein,
            date_created,
            due_date=due_date,
            category=category,
            title_privacy=title_privacy,
            agency_desc_privacy=ag_privacy,
            submission=submission,
            status=status
        )
        self.__assert_request_data_correct(
            self.user_860,
            request,
            self.parent_ein_860,
            title=title,
            description=description,
            agency_description=agency_description,
            agency_ein=self.agency_ein_860,
            date_created=date_created,
            due_date=due_date,
            category=category,
            title_privacy=title_privacy,
            agency_desc_privacy=ag_privacy,
            submission=submission,
            status=status
        )
        # check associated users
        requester = Users.query.filter_by(auth_user_type=user_type_auth.ANONYMOUS_USER).one()
        self.assertEqual(request.requester, requester)
        self.assertFalse(self.user_860 in request.agency_users)
        self.assertTrue(self.admin_860 in request.agency_users)

    def test_create_request_agency_ein(self):
        request = self.rf_agency_860.create_request_as_public_user()
        self.__assert_request_data_correct(
            self.rf_agency_860.public_user,
            request,
            self.parent_ein_860,
            default=True
        )
        self.assertTrue(self.admin_860 in request.agency_users)

    def test_create_request_as_anonymous_user(self):
        request = self.rf.create_request_as_anonymous_user()
        user = Users.query.filter_by(auth_user_type=user_type_auth.ANONYMOUS_USER).one()
        self.__assert_request_data_correct(
            user,
            request,
            request.agency.parent_ein,
            default=True
        )
        self.assertEqual(request.requester, user)

    def test_create_request_as_agency_user(self):
        request = self.rf.create_request_as_agency_user()
        self.__assert_request_data_correct(
            self.rf.agency_user,
            request,
            self.rf.agency_user.agency.parent_ein,
            default=True
        )
        self.assertFalse(self.rf.agency_user in request.agency_users)

    def test_create_request_as_public_user(self):
        request = self.rf.create_request_as_public_user()
        self.__assert_request_data_correct(
            self.rf.public_user,
            request,
            request.agency.parent_ein,
            default=True
        )
        self.assertEqual(request.requester, self.rf.public_user)

    def test_create_request_wrong_dates(self):
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_860, due_date=now, date_created=now)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_860, due_date=now, date_submitted=now)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_860, due_date=now, date_created=tomorrow)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_860, due_date=now, date_submitted=tomorrow)

    def test_create_request_wrong_agency_ein(self):

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_860, agency_ein=self.agency_ein_002)

        with self.assertRaises(AssertionError):
            self.rf_agency_002.create_request(self.user_860)

    def __assert_request_data_correct(self,
                                      user,
                                      request,
                                      agency_parent_ein,
                                      default=False,
                                      title=None,
                                      description=None,
                                      agency_description=None,
                                      agency_ein=None,
                                      date_created=None,
                                      due_date=None,
                                      category='All',
                                      title_privacy=True,
                                      agency_desc_privacy=True,
                                      submission=None,
                                      status=request_status.OPEN):
        request = Requests.query.get(request.id)

        privacy = {"title": title_privacy, "agency_description": agency_desc_privacy}
        agency_ein = agency_ein or user.agency_ein or request.agency_ein
        date_created_local = utc_to_local(date_created or request.date_created, self.tz_name)
        date_submitted_local = get_following_date(date_created_local)

        if default:
            self.assertTrue(request.submission in submission_methods.ALL)
            request_list = [
                type(request.title),
                type(request.description),
            ]
            check_list = [
                str,
                str,
            ]
        else:
            request_list = [
                request.title,
                request.description,
                request.agency_description,
                request.date_created,
                request.submission,
            ]
            check_list = [
                title,
                description,
                agency_description,
                date_created,
                submission,
            ]
        request_list += [
            request.id,
            request.category,
            request.privacy,
            request.agency_ein,
            request.status,
            request.date_submitted,
            request.due_date,
        ]
        check_list += [
            "FOIL-{}-{}-00001".format(datetime.today().year, agency_parent_ein),
            category,
            privacy,
            agency_ein,
            status,
            local_to_utc(date_submitted_local, self.tz_name),
            due_date or get_due_date(date_submitted_local, ACKNOWLEDGMENT_DAYS_DUE, self.tz_name)
        ]
        self.assertEqual(request_list, check_list)

        # check associated events
        event_req_created = Events.query.filter_by(type=event_type.REQ_CREATED).one()
        self.assertEqual(
            [
                event_req_created.user_guid,
                event_req_created.auth_user_type,
                event_req_created.request_id,
                event_req_created.response_id,
                event_req_created.previous_value,
                event_req_created.new_value,
            ],
            [
                user.guid,
                user.auth_user_type,
                request.id,
                None,  # response_id
                None,  # previous_value
                request.val_for_events  # new_value
            ]
        )
        if user.is_agency:
            event_agency_req_created = Events.query.filter_by(type=event_type.AGENCY_REQ_CREATED).one()
            self.assertEqual(
                [
                    event_agency_req_created.user_guid,
                    event_agency_req_created.auth_user_type,
                    event_agency_req_created.request_id,
                    event_agency_req_created.response_id,
                    event_agency_req_created.previous_value,
                    event_agency_req_created.new_value,
                ],
                [
                    user.guid,
                    user.auth_user_type,
                    request.id,
                    None,  # response_id
                    None,  # previous_value
                    None,  # new_value
                ]
            )


class RequestWrapperTests(BaseTestCase, TestHelpers):

    def setUp(self):
        super().setUp()
        self.rf = RequestFactory()
        self.uf = UserFactory()
        self.request = self.rf.create_request_as_anonymous_user()
        self.tz_name = current_app.config["APP_TIMEZONE"]

    def test_set_title(self):
        title = "The Time Has Come"
        self.request.set_title(title)
        request = Requests.query.get(self.request.id)
        self.assertEqual(request.title, title)

    def test_set_agency_description(self):
        agency_description = "To talk of many things."
        self.request.set_agency_description(agency_description)
        request = Requests.query.get(self.request.id)
        self.assertEqual(request.agency_description, agency_description)

    def test_set_title_privacy(self):
        privacy = not self.request.privacy["title"]
        self.request.set_title_privacy(privacy)
        request = Requests.query.get(self.request.id)
        self.assertEqual(request.privacy["title"], privacy)

    def test_set_agency_description_privacy(self):
        privacy = not self.request.privacy["agency_description"]
        self.request.set_agency_description_privacy(privacy)
        request = Requests.query.get(self.request.id)
        self.assertEqual(request.privacy["agency_description"], privacy)

    def test_add_file_default(self):
        response = self.request.add_file()
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.mime_type,
                type(response.title),
                type(response.name),
                type(response.size),
                type(response.hash)
            ],
            [
                self.request.id,
                response_privacy.PRIVATE,
                'text/plain',
                str,  # title
                str,  # filename
                int,  # size
                str,  # hash
            ]
        )
        self.assertTrue(response.size > 0)
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    current_app.config["UPLOAD_DIRECTORY"],
                    self.request.id,
                    response.name
                )
            )
        )
        self.assert_response_event(self.request.id, event_type.FILE_ADDED, response, self.rf.agency_user)

    def test_add_file_custom_without_path(self):
        title = "Having Fun Isn't Hard"
        name = "libary_card"
        privacy = response_privacy.RELEASE_AND_PUBLIC
        response = self.request.add_file(
            title=title,
            name=name,
            privacy=privacy,
            user=self.rf.public_user,
        )
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.title,
                response.name,
                response.mime_type,
                type(response.size),
                type(response.hash)
            ],
            [
                self.request.id,
                privacy,
                title,
                name,
                "text/plain",
                int,  # size
                str,  # hash
            ]
        )
        self.assertTrue(response.size > 0)
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    current_app.config["UPLOAD_DIRECTORY"],
                    self.request.id,
                    response.name
                )
            )
        )
        self.assert_response_event(self.request.id, event_type.FILE_ADDED, response, self.rf.public_user)

    def test_add_file_custom_with_path(self):
        title = "Open Wide"
        response = self.request.add_file(
            title=title,
            name="dont_mind_me",
            filepath=SCREAM_FILE.path,
        )
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.title,
                response.name,
                response.mime_type,
                response.size,
                response.hash
            ],
            [
                self.request.id,
                response_privacy.PRIVATE,
                title,
                SCREAM_FILE.name,
                SCREAM_FILE.mime_type,
                SCREAM_FILE.size,
                SCREAM_FILE.hash
            ]
        )
        self.assert_response_event(self.request.id, event_type.FILE_ADDED, response, self.rf.agency_user)

    def test_add_link(self):
        response = self.request.add_link()

        title = "Urlification"
        url = "http://url.com"
        privacy = response_privacy.RELEASE_AND_PUBLIC
        response_custom = self.request.add_link(title, url, privacy, self.rf.public_user)

        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                type(response.title),
                type(response.url)
            ],
            [
                self.request.id,
                response_privacy.PRIVATE,
                str,  # title
                str,  # url
            ]
        )
        self.assert_response_event(self.request.id, event_type.LINK_ADDED, response, self.rf.agency_user)

        response = Responses.query.get(response_custom.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.title,
                response.url
            ],
            [
                self.request.id,
                privacy,
                title,
                url
            ]
        )
        self.assert_response_event(self.request.id, event_type.LINK_ADDED, response, self.rf.public_user)

    def test_add_note(self):
        response = self.request.add_note()

        content = "I. AM. A. NOTE."
        privacy = response_privacy.RELEASE_AND_PUBLIC
        response_custom = self.request.add_note(content, privacy, self.rf.public_user)

        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                type(response.content)
            ],
            [
                self.request.id,
                response_privacy.PRIVATE,
                str
            ]
        )
        self.assert_response_event(self.request.id, event_type.NOTE_ADDED, response, self.rf.agency_user)

        response = Responses.query.get(response_custom.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.content
            ],
            [
                self.request.id,
                privacy,
                content
            ]
        )
        self.assert_response_event(self.request.id, event_type.NOTE_ADDED, response, self.rf.public_user)

    def test_add_instructions(self):
        response = self.request.add_instructions()

        content = "I want to play a game. In the room to your left you will find..."
        privacy = response_privacy.RELEASE_AND_PUBLIC
        response_custom = self.request.add_instructions(content, privacy, self.rf.public_user)

        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                type(response.content)
            ],
            [
                self.request.id,
                response_privacy.PRIVATE,
                str
            ]
        )
        self.assert_response_event(self.request.id, event_type.INSTRUCTIONS_ADDED, response, self.rf.agency_user)

        response = Responses.query.get(response_custom.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.content
            ],
            [
                self.request.id,
                privacy,
                content
            ]
        )
        self.assert_response_event(self.request.id, event_type.INSTRUCTIONS_ADDED, response, self.rf.public_user)

    def test_acknowledge_days(self):
        days = 30
        info = "Informative information that will inform you."
        due_date = get_due_date(
            utc_to_local(
                self.request.due_date,
                self.tz_name
            ),
            days,
            self.tz_name
        )
        response = self.request.acknowledge(info=info, days=days)
        self.__test_extension(response, determination_type.ACKNOWLEDGMENT, info, due_date)

    def test_acknowledge_date(self):
        date = calendar.addbusdays(datetime.now(), 100)
        response = self.request.acknowledge(date=date)
        due_date = process_due_date(local_to_utc(date, self.tz_name))
        self.__test_extension(response, determination_type.ACKNOWLEDGMENT, str, due_date)

    def test_acknowledge_missing_args(self):
        with self.assertRaises(AssertionError):
            self.request.acknowledge()

    def test_extend_days(self):
        days = 20
        reason = "Reasonable reasoning for the rational reasoner."
        due_date = get_due_date(
            utc_to_local(
                self.request.due_date,
                self.tz_name
            ),
            days,
            self.tz_name
        )
        response = self.request.extend(reason=reason, days=days)
        self.__test_extension(response, determination_type.EXTENSION, reason, due_date)

    def test_extend_date_due_soon(self):
        request = self.rf.create_request_as_anonymous_user(due_date=datetime.utcnow())
        date = calendar.addbusdays(utc_to_local(request.due_date, self.tz_name), 1)
        due_date = process_due_date(local_to_utc(date, self.tz_name))
        response = request.extend(date=date)
        self.__test_extension(
            response, determination_type.EXTENSION, str, due_date, request_status.DUE_SOON, request=request)

    def test_extend_date_overdue(self):
        request = self.rf.create_request_as_anonymous_user(
            due_date=calendar.addbusdays(datetime.utcnow(), -2))
        date = calendar.addbusdays(utc_to_local(request.due_date, self.tz_name), 1)
        due_date = process_due_date(local_to_utc(date, self.tz_name))
        response = request.extend(date=date)
        self.__test_extension(
            response, determination_type.EXTENSION, str, due_date, request_status.OVERDUE, request=request)

    # TODO: prevent users from extending a request to a date that will still result in an OVERDUE status
    def test_extend_bad_due_date(self):
        with self.assertRaises(AssertionError):
            self.request.extend(date=calendar.addbusdays(
                utc_to_local(self.request.due_date, self.tz_name), -1))

    def test_reopen(self):
        date = calendar.addbusdays(utc_to_local(self.request.due_date, self.tz_name), 1)
        response = self.request.reopen(date)
        due_date = process_due_date(local_to_utc(date, self.tz_name))
        self.__test_extension(response, determination_type.REOPENING, None, due_date)
        self.assertEqual(self.request.agency_description, None)

    def __test_extension(self,
                         response,
                         type_,
                         reason,
                         due_date,
                         status=request_status.IN_PROGRESS,
                         user=None,
                         request=None):
        request_id = request.id if request is not None else self.request.id
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                type(response.reason) if isinstance(reason, type) else response.reason,
                response.date
            ],
            [
                request_id,
                response_privacy.RELEASE_AND_PUBLIC,
                type_,
                reason,
                due_date
            ]
        )
        request = Requests.query.get(request_id)
        self.assertEqual(
            [
                request.status,
                request.due_date,
            ],
            [
                status,
                due_date
            ]
        )
        self.assert_response_event(request.id, type_, response, user or self.rf.agency_user)

    def test_close_default(self):
        response = self.request.close()
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                type(response.reason)
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                str
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.rf.agency_user)

    def test_close_custom(self):
        reason_ids = [1, 2, 3]
        response_custom = self.request.close(reason_ids, self.rf.public_user)
        response = Responses.query.get(response_custom.id)
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                response.reason
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons(reason_ids)
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.rf.public_user)

    def test_deny_default(self):
        response = self.request.deny()
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                type(response.reason)
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.DENIAL,
                str
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.rf.agency_user)

    def test_deny_custom(self):
        reason_ids = [19, 20, 21]
        response_custom = self.request.deny(reason_ids, self.rf.public_user)
        response = Responses.query.get(response_custom.id)
        response = Responses.query.get(response.id)
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                response.reason
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.DENIAL,
                format_determination_reasons(reason_ids)
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.rf.public_user)

    def test_set_due_soon(self):
        self.__test_due_soon_or_overdue(
            request_status.DUE_SOON,
            calendar.addbusdays(
                datetime.utcnow(), current_app.config["DUE_SOON_DAYS_THRESHOLD"]
            ).replace(hour=23, minute=59, second=59, microsecond=0),
        )

    def test_set_due_soon_no_shift(self):
        self.__test_due_soon_or_overdue(request_status.DUE_SOON, no_shift=True)

    def test_set_overdue(self):
        self.__test_due_soon_or_overdue(
            request_status.OVERDUE,
            calendar.addbusdays(
                datetime.utcnow(), -1
            ).replace(microsecond=0)
        )

    def test_set_overdue_no_shift(self):
        self.__test_due_soon_or_overdue(request_status.OVERDUE, no_shift=True)

    def __test_due_soon_or_overdue(self, status, due_date=None, no_shift=False):
        if no_shift:
            due_date = self.request.due_date
            date_submitted = self.request.date_submitted
            date_created = self.request.date_created

            {request_status.DUE_SOON: self.request.set_due_soon,
             request_status.OVERDUE: self.request.set_overdue
            }[status](shift_dates=False)

            request = Requests.query.get(self.request.id)
            self.assertEqual(
                [
                    request.status,
                    request.due_date,
                    request.date_submitted,
                    request.date_created
                ],
                [
                    status,
                    due_date,
                    date_submitted,
                    date_created
                ]
            )
        else:
            shift = due_date - self.request.due_date
            date_submitted = self.request.date_submitted + shift
            date_created = self.request.date_created + shift
            old_status = self.request.status

            {request_status.DUE_SOON: self.request.set_due_soon,
             request_status.OVERDUE: self.request.set_overdue
             }[status]()

            request = Requests.query.get(self.request.id)
            self.assertEqual(
                [
                    request.status,
                    request.due_date,
                    request.date_submitted,
                    request.date_created,
                    # TODO: request.agency_description_release_date
                ],
                [
                    status,
                    due_date,
                    date_submitted,
                    date_created
                ]
            )
            event = Events.query.filter_by(type=event_type.REQ_STATUS_CHANGED).one()
            self.assertEqual(
                [
                    event.request_id,
                    event.user_guid,
                    event.auth_user_type,
                    event.previous_value,
                    event.new_value,
                    event.response_id
                ],
                [
                    self.request.id,
                    None,  # user_guid
                    None,  # auth_user_type
                    {"status": old_status},
                    {"status": status},
                    None
                ]
            )

    def test_add_user_anonymous(self):
        self.__test_add_user_default(
            self.uf.create_anonymous_user(),
            user_type_request.REQUESTER,
            role_name.ANONYMOUS
        )

    def test_add_user_public(self):
        self.__test_add_user_default(
            self.uf.create_public_user(),
            user_type_request.REQUESTER,
            role_name.PUBLIC_REQUESTER
        )

    def test_add_user_agency_inactive(self):
        self.__test_add_user_default(
            self.uf.create_agency_user(agency_ein=self.request.agency.ein),
            user_type_request.AGENCY,
            role_name.AGENCY_HELPER
        )

    def test_add_user_agency_active(self):
        self.__test_add_user_default(
            self.uf.create_agency_user(agency_ein=self.request.agency.ein,
                                       is_agency_active=True),
            user_type_request.AGENCY,
            role_name.AGENCY_OFFICER
        )

    def test_add_user_agency_admin(self):
        self.__test_add_user_default(
            self.uf.create_agency_admin(agency_ein=self.request.agency.ein),
            user_type_request.AGENCY,
            role_name.AGENCY_ADMIN
        )

    def __test_add_user_default(self, user, request_user_type, role):
        user_request = self.request.add_user(user)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.assertEqual(
            [
                user_request.request_id,
                user_request.request_user_type,
                user_request.permissions
            ],
            [
                self.request.id,
                request_user_type,
                Roles.query.filter_by(name=role).one().permissions
            ]
        )
        self.__assert_user_request_event(event_type.USER_ADDED, user_request, self.rf.agency_user)

    def test_add_user_custom_agent(self):
        user = self.uf.create_anonymous_user()
        agency_user = self.uf.create_agency_user(agency_ein=self.request.agency.ein)
        user_request = self.request.add_user(user, agent=agency_user)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.__assert_user_request_event(event_type.USER_ADDED, user_request, agency_user)

    def test_add_user_custom_role(self):
        user = self.uf.create_anonymous_user()
        rname = role_name.PUBLIC_REQUESTER
        user_request = self.request.add_user(user, role=rname)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.assertEqual(
            user_request.permissions,
            Roles.query.filter_by(name=rname).one().permissions
        )

    def test_add_user_custom_permissions(self):
        user = self.uf.create_anonymous_user()
        permissions = permission.ADD_LINK
        user_request = self.request.add_user(user, permissions=permissions)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.assertEqual(user_request.permissions, permissions)

    def test_edit_user_set_permissions(self):
        user = self.uf.create_public_user()
        user_request = self.request.add_user(user)
        old_permissions = user_request.permissions
        permissions = [permission.ADD_FILE, permission.ADD_OFFLINE_INSTRUCTIONS]
        self.request.edit_user(user, perms_set=permissions)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.assertEqual(user_request.permissions, reduce(ior, permissions))
        self.__assert_user_request_event(
            event_type.USER_PERM_CHANGED, user_request, self.rf.agency_user, old_permissions)

    def test_edit_user_add_permissions(self):
        user = self.uf.create_public_user()
        user_request = self.request.add_user(user)
        old_permissions = user_request.permissions
        permissions = [permission.ADD_OFFLINE_INSTRUCTIONS]
        self.request.edit_user(user, perms_add=permissions)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.assertEqual(user_request.permissions, permissions[0] | old_permissions)
        self.__assert_user_request_event(
            event_type.USER_PERM_CHANGED, user_request, self.rf.agency_user, old_permissions)

    def test_edit_user_remove_permissions(self):
        user = self.uf.create_public_user()
        user_request = self.request.add_user(user)
        old_permissions = [user_request.permissions]
        self.request.edit_user(user, perms_remove=old_permissions)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.assertEqual(user_request.permissions, permission.NONE)
        self.__assert_user_request_event(
            event_type.USER_PERM_CHANGED, user_request, self.rf.agency_user, old_permissions[0])

    def test_edit_user_as_agent(self):
        user = self.uf.create_anonymous_user()
        agency_user = self.uf.create_agency_user(agency_ein=self.request.agency.ein)
        user_request = self.request.add_user(user)
        old_permissions = user_request.permissions
        self.request.edit_user(user, perms_set=permission.NONE, agent=agency_user)
        user_request = UserRequests.query.filter_by(user_guid=user.guid).one()
        self.__assert_user_request_event(
            event_type.USER_PERM_CHANGED, user_request, agency_user, old_permissions)

    def test_edit_user_missing_permissions(self):
        user = self.uf.create_anonymous_user()
        with self.assertRaises(AssertionError):
            self.request.edit_user(user)

    def test_remove_user(self):
        user = self.uf.create_anonymous_user()
        user_request = self.request.add_user(user)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.request.remove_user(user)
        self.__assert_user_request_event(event_type.USER_REMOVED, user_request, self.rf.agency_user)
        self.assertTrue(UserRequests.query.filter_by(user_guid=user.guid).first() is None)

    def test_remove_user_as_agent(self):
        user = self.uf.create_anonymous_user()
        agency_user = self.uf.create_agency_user(agency_ein=self.request.agency.ein)
        user_request = self.request.add_user(user)
        user_request = UserRequests.query.filter_by(user_guid=user_request.user_guid).one()
        self.request.remove_user(user, agent=agency_user)
        self.__assert_user_request_event(event_type.USER_REMOVED, user_request, agency_user)
        self.assertTrue(UserRequests.query.filter_by(user_guid=user.guid).first() is None)

    def test_destructor(self):
        response = self.request.add_file()
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    current_app.config["UPLOAD_DIRECTORY"],
                    self.request.id,
                    response.name
                )
            )
        )
        request_id = self.request.id
        del self.request
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    current_app.config["UPLOAD_DIRECTORY"],
                    request_id,
                    response.name
                )
            )
        )

    def __assert_user_request_event(self, type_, user_request, user, old_permissions=None):
        # get latest event with type `type_`
        event = Events.query.filter_by(type=type_).order_by(Events.timestamp.desc()).first()
        self.assertEqual(
            [
                event.request_id,
                event.user_guid,
                event.auth_user_type,
                event.previous_value,
                event.new_value
            ],
            [
                self.request.id,
                user.guid,
                user.auth_user_type,
                {"permissions": old_permissions} if old_permissions is not None else None,
                user_request.val_for_events
            ]
        )
