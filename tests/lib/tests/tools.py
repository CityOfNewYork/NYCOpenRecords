from datetime import datetime, timedelta
from flask import current_app
from app.models import (
    Users,
    Requests,
    Agencies,
    Events,
)
from app.constants import (
    user_type_auth,
    request_status,
    submission_methods,
    ACKNOWLEDGMENT_DAYS_DUE,
)
from app.lib.date_utils import (
    local_to_utc,
    utc_to_local,
    get_following_date,
)
from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    UserFactory,
    RequestsFactory,
    RequestWrapper,
)


class UserFactoryTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.uf = UserFactory()
        self.agency_ein = Agencies.query.first().ein

    def test_create_user(self):
        auth_type = user_type_auth.PUBLIC_USER_NYC_ID
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

        # user 1 (default kwargs)
        u1 = self.uf.create_user(auth_type)

        # user 2
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

    def test_create_user_wrong_agency_ein(self):

        with self.assertRaises(AssertionError):
            self.uf.create_user(user_type_auth.AGENCY_USER)

        with self.assertRaises(AssertionError):
            self.uf.create_user(user_type_auth.ANONYMOUS_USER, agency_ein=self.agency_ein)

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
        u2 = self.uf.create_agency_user(self.agency_ein)

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
            fuzzy=True
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
                                   mailing_address=None):
        """
        Retrieves Users database records and compares its data to the supplied argument value.
        If fuzzy is True, only types are checked for the user-specific kwargs.
        """
        user = Users.query.get((user.guid, user.auth_user_type))
        user_list = [
            user.auth_user_type,
            user.agency_ein,
            user.email_validated,
            user.terms_of_use_accepted
        ]
        check_list = [
            auth_type,
            agency_ein,
            email_validated,
            terms_of_use_accepted,
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
                mailing_address
            ]

        self.assertEqual(user_list, check_list)

    def test_generate_guid(self):
        pass


class RequestsFactoryTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.agency_ein_1 = "0860"
        self.parent_ein_1 = "860"
        self.agency_ein_2 = "0002"
        self.user_1 = UserFactory().create_agency_user(self.agency_ein_1)
        self.rf = RequestsFactory()
        self.rf_agency_1 = RequestsFactory(agency_ein=self.agency_ein_1)
        self.rf_agency_2 = RequestsFactory(agency_ein=self.agency_ein_2)
        self.tz_name = current_app.config["APP_TIMEZONE"]

    def test_create_request(self):
        r1 = self.rf.create_request(self.user_1)  # TODO: test same with rf_agency_1
        r1 = Requests.query.get(r1.id)

        self.assertEqual(
            [
                r1.id,
                type(r1.title),
                type(r1.description),
                # r1.category, TODO
                # r1.privacy, TODO
                r1.agency_ein,
                r1.status
            ],
            [
                "FOIL-{}-{}-00001".format(datetime.today().year, self.parent_ein_1),
                str,  # title
                str,  # description
                self.user_1.agency_ein,
                request_status.OPEN
            ]
        )
        # check submission method
        self.assertTrue(r1.submission in submission_methods.ALL)
        # dates
        self.assertTrue(r1.date_submitted == local_to_utc(
            get_following_date(utc_to_local(r1.date_created, self.tz_name)),
            self.tz_name))
        # TODO: date_due

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