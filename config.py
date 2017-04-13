import os
from datetime import timedelta

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)


class Config:
    NYC_GOV_BASE = 'www1.nyc.gov'
    WTF_CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    LOGFILE_DIRECTORY = (os.environ.get('LOGFILE_DIRECTORY') or
                         os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logs/'))

    APP_VERSION_STRING = os.environ.get('APP_VERSION_STRING')
    APP_TIMEZONE = os.environ.get('APP_TIMEZONE') or 'US/Eastern'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE') == 'True'

    # Note: BASE_URL and VIEW_REQUEST_ENDPOINT used for the automatic status update job (jobs.py)
    BASE_URL = os.environ.get('BASE_URL')
    VIEW_REQUEST_ENDPOINT = os.environ.get('VIEW_REQUEST_ENDPOINT')

    AGENCY_DATA = (os.environ.get('AGENCY_DATA') or
                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'agencies.csv'))
    REASON_DATA = (os.environ.get('REASONS_DATA') or
                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'reasons.csv'))
    STAFF_DATA = (os.environ.get('STAFF_DATA') or
                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'staff.csv'))

    DUE_SOON_DAYS_THRESHOLD = os.environ.get('DUE_SOON_DAYS_THRESHOLD') or 2

    # SFTP
    USE_SFTP = os.environ.get('USE_SFTP') == "True"
    SFTP_HOSTNAME = os.environ.get('SFTP_HOSTNAME')
    SFTP_PORT = os.environ.get('SFTP_PORT')
    SFTP_USERNAME = os.environ.get('SFTP_USERNAME')
    SFTP_RSA_KEY_FILE = os.environ.get('SFTP_RSA_KEY_FILE')
    SFTP_UPLOAD_DIRECTORY = os.environ.get('SFTP_UPLOAD_DIRECTORY')

    # File Encryption
    USE_ENCRYPTION = os.environ.get('USE_ENCRYPTION') == 'True'
    ENCRYPTION_HOST = os.environ.get('ENCRYPTION_HOST') or os.environ.get('DATABASE_HOST')
    ENCRYPTION_USERNAME = os.environ.get('ENCRYPTION_USERNAME')
    ENCRYPTION_RSA_KEY_FILEPATH = os.environ.get('ENCRYPTION_RSA_KEY_FILEPATH')
    ENCRYPTION_GPG_KEY_FILENAME = os.environ.get('ENCRYPTION_GPG_KEY_FILENAME') or "key.gpg"

    # Authentication Settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('PERMANENT_SESSION_LIFETIME', 30)))
    SAML_PATH = (os.environ.get('SAML_PATH') or
                os.path.join(os.path.abspath(os.path.dirname(__file__)), 'saml'))

    USE_OAUTH = os.environ.get('USE_OAUTH') == "True"
    WEB_SERVICES_URL = os.environ.get('WEB_SERVICES_URL')
    VERIFY_WEB_SERVICES = os.environ.get('VERIFY_WEB_SERVICES') == "True"
    NYC_ID_USERNAME = os.environ.get('NYC_ID_USERNAME')
    NYC_ID_PASSWORD = os.environ.get('NYC_ID_PASSWORD')

    USE_LDAP = os.environ.get('USE_LDAP') == "True"
    LDAP_SERVER = os.environ.get('LDAP_SERVER') or None
    LDAP_PORT = os.environ.get('LDAP_PORT') or None
    LDAP_USE_TLS = os.environ.get('LDAP_USE_TLS') == "True"
    LDAP_KEY_PATH = os.environ.get('LDAP_KEY_PATH') or None
    LDAP_SA_BIND_DN = os.environ.get('LDAP_SA_BIND_DN') or None
    LDAP_SA_PASSWORD = os.environ.get('LDAP_SA_PASSWORD') or None
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN') or None

    # Database Settings
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    # Redis Settings
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = os.environ.get('REDIS_PORT') or '6379'
    CELERY_REDIS_DB = 0
    SESSION_REDIS_DB = 1
    UPLOAD_REDIS_DB = 2
    EMAIL_REDIS_DB = 3

    # Celery Settings
    CELERY_BROKER_URL = 'redis://{redis_host}:{redis_port}/{celery_redis_db}'.format(
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        celery_redis_db=CELERY_REDIS_DB
    )
    CELERY_RESULT_BACKEND = 'redis://{redis_host}:{redis_port}/{celery_redis_db}'.format(
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        celery_redis_db=CELERY_REDIS_DB
    )

    # Flask-Mail Settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', "True") == "True"
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = os.environ.get('MAIL_SUBJECT_PREFIX')
    MAIL_SENDER = os.environ.get('MAIL_SENDER')

    # TODO: should be a constant
    EMAIL_TEMPLATE_DIR = 'email_templates/'

    # Flask-SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # remove once this becomes the default

    # Upload Settings
    # TODO: change naming since quarantine is used as a serving directory as well
    UPLOAD_QUARANTINE_DIRECTORY = (os.environ.get('UPLOAD_QUARANTINE_DIRECTORY') or
                                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quarantine/incoming/'))
    UPLOAD_SERVING_DIRECTORY = (os.environ.get('UPLOAD_DIRECTORY') or
                                os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quarantine/outgoing/'))
    UPLOAD_DIRECTORY = (os.environ.get('UPLOAD_DIRECTORY') or
                        os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/')
                        if not USE_SFTP else SFTP_UPLOAD_DIRECTORY)
    VIRUS_SCAN_ENABLED = os.environ.get('VIRUS_SCAN_ENABLED') == "True"
    MAGIC_FILE = (os.environ.get('MAGIC_FILE') or
                  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'magic'))

    # ReCaptcha
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

    # ElasticSearch settings
    ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST') or "localhost:9200"
    ELASTICSEARCH_ENABLED = os.environ.get('ELASTICSEARCH_ENABLED') == "True"
    ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX') or "requests"
    ELASTICSEARCH_USE_SSL = os.environ.get('ELASTICSEARCH_USE_SSL') == "True"
    ELASTICSEARCH_VERIFY_CERTS = os.environ.get('ELASTICSEARCH_VERIFY_CERTS') == "True"
    ELASTICSEARCH_USERNAME = os.environ.get('ELASTICSEARCH_USERNAME')
    ELASTICSEARCH_PASSWORD = os.environ.get('ELASTICSEARCH_PASSWORD')
    ELASTICSEARCH_HTTP_AUTH = ((ELASTICSEARCH_USERNAME,
                                ELASTICSEARCH_PASSWORD)
                               if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
                               else None)
    # https://www.elastic.co/blog/index-vs-type

    @staticmethod
    def init_app(app):
        pass


def get_sqlalchemy_database_uri(name, host="localhost", port="5432", env="DATABASE_URL"):
    """
    Returns the sqlalchemy database uri with the following methods,
    with each subsequent method serving as a fallback to the one prior:
    - Fetch from supplied env(vironment variable key)
    - Assemble from env vars "DATABSE_HOST", "DATABASE_PORT", "DATABASE_NAME"
    - Assemble from supplied name, host, and port

    :param name: the default database name
    :param host: the default database host
    :param port: the default database port
    """
    user_, host_, port_, name_ = os.environ.get("DATABASE_USER"), \
                                 os.environ.get("DATABASE_HOST"), \
                                 os.environ.get("DATABASE_PORT"), \
                                 os.environ.get("DATABASE_NAME")
    if user_:
        host_ = "@".join((user_, host_))

    uri_template = "postgresql://{}/{}"

    return os.environ.get(env) or (
        uri_template.format(":".join((host_, port_)), name_)
        if host_ and port_ and name_
        else uri_template.format(":".join((host, port)), name)
    )


class DevelopmentConfig(Config):
    DEBUG = True
    VIRUS_SCAN_ENABLED = os.environ.get('VIRUS_SCAN_ENABLED') == "True"
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 2500
    MAIL_USE_TLS = False
    MAIL_SUBJECT_PREFIX = '[OpenRecords Development]'
    MAIL_SENDER = 'OpenRecords - Dev Admin <donotreply@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri('openrecords_v2_0_dev')
    # Using Vagrant? Try: 'postgresql://vagrant@/openrecords_v2_0_dev'
    ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX') or "requests_dev"
    MAGIC_FILE = os.environ.get('MAGIC_FILE')


class TestingConfig(Config):
    TESTING = True
    VIRUS_SCAN_ENABLED = True
    USE_SFTP = False
    UPLOAD_DIRECTORY = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data_test/')
    MAIL_SUBJECT_PREFIX = '[OpenRecords Testing]'
    MAIL_SENDER = 'OpenRecords - Testing Admin <donotreply@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri('openrecords_v2_0_test', env="TEST_DATABASE_URL")
    ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX') or "requests_test"


class ProductionConfig(Config):
    VIRUS_SCAN_ENABLED = True
    ELASTICSEARCH_ENABLED = True
    SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri("openrecords_v2_0")

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
