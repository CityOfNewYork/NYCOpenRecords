import os


DATA_FIXTURES_DIR = "fixtures/data/"

PNG_FILE_NAME = "scream.png"
PNG_FILE_PATH = os.path.join(
    os.path.abspath(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    ),
    DATA_FIXTURES_DIR,
    PNG_FILE_NAME)

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
