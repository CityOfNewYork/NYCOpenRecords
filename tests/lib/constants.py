import os

NON_ANON_USER_GUID_LEN = 6

DATA_FIXTURES_DIR = "fixtures/data/"


class _Fixture(object):
    def __init__(self, name, size, hash, mime_type):
        self.__name = name
        self.__size = size
        self.__hash = hash
        self.__path = os.path.join(
            os.path.abspath(
                os.path.dirname(
                    os.path.dirname(__file__)
                )
            ),
            DATA_FIXTURES_DIR,
            self.__name
        )
        self.__mime_type = mime_type

    @property
    def name(self):
        return self.__name

    @property
    def size(self):
        return self.__size

    @property
    def hash(self):
        return self.__hash

    @property
    def path(self):
        return self.__path

    @property
    def mime_type(self):
        return self.__mime_type


SCREAM_FILE = _Fixture(
    "scream.png",
    6646,
    '1a7c89197e0fdb9ae6dc584567023239b56ab9cb',
    'image/png'
)

USERS_CSV_FILE_NAME = "test_users.csv"
USERS_CSV_FILE_PATH = os.path.join(
    os.path.abspath(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    ),
    DATA_FIXTURES_DIR,
    USERS_CSV_FILE_NAME)
AGENCIES_CSV_FILE_NAME = "test_agencies.csv"
AGENCIES_CSV_FILE_PATH = os.path.join(
    os.path.abspath(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    ),
    DATA_FIXTURES_DIR,
    AGENCIES_CSV_FILE_NAME)

NON_ANON_USER_GUID_LEN = 6
