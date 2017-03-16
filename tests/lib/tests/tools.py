from datetime import datetime, timedelta
from flask import current_app
from app.models import (
    Users,
    Requests,
    Agencies,
    Events,
)
from app.constants import (
    event_type,
    user_type_auth,
    request_status,
    submission_methods,
    ACKNOWLEDGMENT_DAYS_DUE,
)
from app.lib.date_utils import (
    local_to_utc,
    utc_to_local,
    get_due_date,
    get_following_date,
)
from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    UserFactory,
    RequestFactory,
    RequestWrapper,
)


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
        organization = "Supa Shrimp Inc."
        phone_number = "(111) 111-1111"
        fax_number = "(222) 222-2222"
        mailing_address = {
            "address_one": "P. Sherman 42",
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
        self.agency_ein_1 = "0860"
        self.parent_ein_1 = "860"
        self.agency_ein_2 = "0002"
        self.user_1 = UserFactory().create_agency_user(self.agency_ein_1)
        self.rf = RequestFactory()
        self.rf_agency_1 = RequestFactory(agency_ein=self.agency_ein_1)
        self.rf_agency_2 = RequestFactory(agency_ein=self.agency_ein_2)
        self.tz_name = current_app.config["APP_TIMEZONE"]
        # TODO: create agency admins and test if assigned

    def test_create_request_default(self):
        request = self.rf.create_request(self.user_1)
        self.__assert_request_data_correct(
            self.user_1,
            request,
            self.parent_ein_1,
            default=True,
        )
        # check associated users
        requester = Users.query.filter_by(auth_user_type=user_type_auth.ANONYMOUS_USER).one()
        self.assertEqual(request.requester, requester)
        self.assertTrue(self.user_1 in request.agency_users)

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
            self.user_1,
            title,
            description,
            agency_description,
            self.user_1.agency_ein,
            date_created,
            due_date=due_date,
            category=category,
            title_privacy=title_privacy,
            agency_desc_privacy=ag_privacy,
            submission=submission,
            status=status
        )
        self.__assert_request_data_correct(
            self.user_1,
            request,
            self.parent_ein_1,
            title=title,
            description=description,
            agency_description=agency_description,
            agency_ein=self.agency_ein_1,
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
        self.assertTrue(self.user_1 in request.agency_users)

    def test_create_request_agency_ein(self):
        # TODO: rf_agency_1
        pass

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

    def test_create_request_as_public_user(self):
        request = self.rf.create_request_as_public_user()
        self.__assert_request_data_correct(
            self.rf.public_user,
            request,
            request.agency.parent_ein,
            default=True
        )
        self.assertEqual(request.requester, self.rf.public_user)
        # self.assertTrue(self.rf.agency_user in request.agency_users)

    def test_create_request_wrong_dates(self):
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_1, due_date=now, date_created=now)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_1, due_date=now, date_submitted=now)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_1, due_date=now, date_created=tomorrow)

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_1, due_date=now, date_submitted=tomorrow)

    def test_create_request_wrong_agency_ein(self):

        with self.assertRaises(AssertionError):
            self.rf.create_request(self.user_1, agency_ein=self.agency_ein_2)

        with self.assertRaises(AssertionError):
            self.rf_agency_2.create_request(self.user_1)

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
                type(request.agency_description)
            ]
            check_list = [
                str,
                str,
                str
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
