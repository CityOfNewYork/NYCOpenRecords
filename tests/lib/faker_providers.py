"""
    Faker Providers including aliases for OpenRecords entities.
"""
import random
from faker import Faker
from faker.providers import BaseProvider
from app.lib.user_information import create_mailing_address

fake = Faker()


class UserDataProvider(BaseProvider):

    def user_title(self):
        return fake.job()

    def organization(self):
        return fake.company()

    def fax_number(self):
        return fake.phone_number()

    def mailing_address(self):
        return create_mailing_address(
            fake.street_address(),
            fake.city(),
            fake.state_abbr(),
            fake.zipcode(),
        )


class RequestDataProvider(BaseProvider):

    def title(self):
        return fake.sentence().title()

    def description(self):
        return '\n'.join(fake.paragraphs(random.randrange(3, 6)))

    def agency_request_summary(self):
        return fake.paragraph()


class FileDataProvider(BaseProvider):

    CHARS_MIN = 1000
    CHARS_MAX = 5000

    def file_content(self):
        return fake.text(random.randrange(self.CHARS_MIN, self.CHARS_MAX))


fake.add_provider(UserDataProvider)
fake.add_provider(RequestDataProvider)
fake.add_provider(FileDataProvider)
