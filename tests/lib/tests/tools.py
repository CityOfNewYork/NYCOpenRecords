from app.models import (
    Users,
    Requests,
)
from app.constants import user_type_auth
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

        # user 1
        u1 = self.uf.create_user(auth_type)
        u1 = Users.query.get((u1.guid, u1.auth_user_type))

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
        u2 = Users.query.get((u2.guid, u2.auth_user_type))

        # user 1
        self.assertEquals(
            [
                u1.auth_user_type,
                u1.agency_ein,
                type(u1.email),
                type(u1.first_name),
                type(u1.last_name),
                type(u1.title),
                type(u1.organization),
                type(u1.phone_number),
                type(u1.fax_number),
                type(u1.mailing_address),
                u1.email_validated,
                u1.terms_of_use_accepted
            ],
            [
                auth_type,
                None,  # agency_ein
                str,  # email
                str,  # first name
                str,  # last name
                str,  # title
                str,  # organization
                str,  # phone_number
                str,  # fax_number
                dict,  # mailing_address
                True,  # email_validataed
                True,  # terms_of_use_accepted
            ]
        )

        # user 2
        self.assertEqual(
            [
                u2.auth_user_type,
                u2.agency_ein,
                u2.email,
                u2.first_name,
                u2.last_name,
                u2.title,
                u2.organization,
                u2.phone_number,
                u2.fax_number,
                u2.mailing_address,
                u2.email_validated,
                u2.terms_of_use_accepted
            ],
            [
                auth_type,
                None,
                email,
                first_name,
                last_name,
                title,
                organization,
                phone_number,
                fax_number,
                mailing_address,
                email_validated,
                terms_of_use_accepted
            ]
        )

    def test_create_user_agency_ein(self):
        # TODO: test both agency_ein assertions
        pass

    def test_create_anonymous_user(self):
        # TODO: check email_validated and terms_of_use_accepted
        pass

    def test_create_agency_user(self):
        pass

    def test_create_public_user(self):
        pass

    def test_generate_guid(self):
        pass


class RequestsFactoryTest(BaseTestCase):

    def setUp(self):
        self.rf = RequestsFactory()
        # TODO: self.rf_agency = RequestsFactory(agency_ein=)
