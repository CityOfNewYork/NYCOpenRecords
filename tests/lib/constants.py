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

NON_ANON_USER_GUID_LEN = 6
