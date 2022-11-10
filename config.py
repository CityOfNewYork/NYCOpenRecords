from datetime import timedelta, datetime

import os, redis
from dotenv import load_dotenv

from app.constants import OPENRECORDS_DL_EMAIL

basedir = os.path.abspath(os.path.dirname(__file__))

dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)


class Config:
    NYC_GOV_BASE = 'www1.nyc.gov'
    WTF_CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    LOGFILE_DIRECTORY = (os.environ.get('LOGFILE_DIRECTORY') or
                         os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logs/'))

    APP_LAUNCH_DATE = datetime.strptime(os.environ.get('APP_LAUNCH_DATE'), '%Y-%m-%d') or datetime.today()
    APP_VERSION_STRING = os.environ.get('APP_VERSION_STRING')
    APP_TIMEZONE = os.environ.get('APP_TIMEZONE') or 'US/Eastern'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE') == 'True'
    PREFERRED_URL_SCHEME = 'https'
    OPENRECORDS_AGENCY_SUPPORT_DL = os.environ.get('OPENRECORDS_AGENCY_SUPPORT_DL') or OPENRECORDS_DL_EMAIL

    # Note: BASE_URL and VIEW_REQUEST_ENDPOINT used for the automatic status update job (jobs.py)
    BASE_URL = os.environ.get('BASE_URL')
    VIEW_REQUEST_ENDPOINT = os.environ.get('VIEW_REQUEST_ENDPOINT')

    AGENCY_DATA = (os.environ.get('AGENCY_DATA') or
                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'agencies.json'))
    CUSTOM_REQUEST_FORMS_DATA = (os.environ.get('CUSTOM_REQUEST_FORMS_DATA') or
                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'custom_request_forms.json'))
    LETTER_TEMPLATES_DATA = (os.environ.get('LETTER_TEMPLATES_DATA') or
                             os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'letter_templates.csv'))
    REASON_DATA = (os.environ.get('REASONS_DATA') or
                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'reasons.csv'))
    STAFF_DATA = (os.environ.get('STAFF_DATA') or
                  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'staff.csv'))
    ENVELOPE_TEMPLATES_DATA = (os.environ.get('ENVELOPE_TEMPLATES_DATA') or
                  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'envelope_templates.csv'))
    LATEX_TEMPLATE_DIRECTORY = (os.environ.get('LATEX_TEMPLATE_DIRECTORY') or
                                os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app', 'templates', 'latex'))
    JSON_SCHEMA_DIRECTORY = (os.environ.get('JSON_SCHEMA_DIRECTORY') or
                             os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app', 'constants', 'schemas'))
    LOGIN_IMAGE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app', 'static', 'img', 'login.png')

    DUE_SOON_DAYS_THRESHOLD = os.environ.get('DUE_SOON_DAYS_THRESHOLD') or 2

    # SFTP
    USE_SFTP = os.environ.get('USE_SFTP') == "True"
    SFTP_HOSTNAME = os.environ.get('SFTP_HOSTNAME')
    SFTP_PORT = os.environ.get('SFTP_PORT')
    SFTP_USERNAME = os.environ.get('SFTP_USERNAME')
    SFTP_PASSWORD = os.environ.get('SFTP_PASSWORD', '').replace("'", "")
    SFTP_RSA_KEY_FILE = os.environ.get('SFTP_RSA_KEY_FILE')
    SFTP_UPLOAD_DIRECTORY = os.environ.get('SFTP_UPLOAD_DIRECTORY')

    # Authentication Settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('PERMANENT_SESSION_LIFETIME', 20)))
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'redis')
    USE_SAML = os.environ.get('USE_SAML') == "True"
    MFA_ENCRYPT_FILE = os.environ.get('MFA_ENCRYPT_FILE')

    AUTH_TYPE = 'None'

    if USE_SAML:
        SAML_PATH = (os.environ.get('SAML_PATH') or
                     os.path.join(os.path.abspath(os.path.dirname(__file__)), 'saml'))
        WEB_SERVICES_URL = os.environ.get('SAML_WEB_SERVICES_URL')
        VERIFY_WEB_SERVICES = os.environ.get('SAML_VERIFY_WEB_SERVICES') == "True"
        NYC_ID_USERNAME = os.environ.get('SAML_NYC_ID_USERNAME')
        NYC_ID_PASSWORD = os.environ.get('SAML_NYC_ID_PASSWORD')
        AUTH_TYPE = 'saml'

    USE_LDAP = os.environ.get('USE_LDAP') == "True"
    if USE_LDAP:
        LDAP_SERVER = os.environ.get('LDAP_SERVER') or None
        LDAP_PORT = os.environ.get('LDAP_PORT') or None
        LDAP_USE_TLS = os.environ.get('LDAP_USE_TLS') == "True"
        LDAP_KEY_PATH = os.environ.get('LDAP_KEY_PATH') or None
        LDAP_SA_BIND_DN = os.environ.get('LDAP_SA_BIND_DN') or None
        LDAP_SA_PASSWORD = os.environ.get('LDAP_SA_PASSWORD') or None
        LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN') or None
        AUTH_TYPE = 'ldap'

    USE_LOCAL_AUTH = os.environ.get('USE_LOCAL_AUTH') == "True"
    if USE_LOCAL_AUTH:
        AUTH_TYPE = 'local_auth'

    # Redis Settings
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = os.environ.get('REDIS_PORT') or '6379'
    CELERY_REDIS_DB = 0
    SESSION_REDIS_DB = 1
    UPLOAD_REDIS_DB = 2
    EMAIL_REDIS_DB = 3

    SESSION_REDIS = redis.StrictRedis(db=SESSION_REDIS_DB,
                                      host=REDIS_HOST,
                                      port=REDIS_PORT)

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

    ERROR_RECIPIENTS = (os.environ.get('ERROR_RECIPIENTS', None) or OPENRECORDS_DL_EMAIL).split(',')

    # TODO: should be a constant
    EMAIL_TEMPLATE_DIR = 'email_templates/'

    # Flask-SQLAlchemy
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # remove once this becomes the default
    SQLALCHEMY_POOL_SIZE = 1

    # Upload Settings
    # TODO: change naming since quarantine is used as a serving directory as well
    UPLOAD_QUARANTINE_DIRECTORY = (os.environ.get('UPLOAD_QUARANTINE_DIRECTORY') or
                                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quarantine/incoming/'))
    UPLOAD_SERVING_DIRECTORY = (os.environ.get('UPLOAD_SERVING_DIRECTORY') or
                                os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quarantine/outgoing/'))
    UPLOAD_DIRECTORY = (os.environ.get('UPLOAD_DIRECTORY') or
                        os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/')
                        if not USE_SFTP else SFTP_UPLOAD_DIRECTORY)
    VIRUS_SCAN_ENABLED = os.environ.get('VIRUS_SCAN_ENABLED') == "True"
    MAGIC_FILE = (os.environ.get('MAGIC_FILE') or
                  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'magic'))

    # ReCaptcha
    RECAPTCHA3_PUBLIC_KEY = os.environ.get("RECAPTCHA_SITE_KEY_V3", "")
    RECAPTCHA3_PRIVATE_KEY = os.environ.get("RECAPTCHA_SECRET_KEY_V3", "")

    # ElasticSearch settings
    ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST') or "localhost:9200"
    ELASTICSEARCH_ENABLED = os.environ.get('ELASTICSEARCH_ENABLED') == "True"
    ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX') or "requests"
    ELASTICSEARCH_USE_SSL = os.environ.get('ELASTICSEARCH_USE_SSL') == "True"
    ELASTICSEARCH_VERIFY_CERTS = os.environ.get('ELASTICSEARCH_VERIFY_CERTS') == "True"
    ELASTICSEARCH_USERNAME = os.environ.get('ELASTICSEARCH_USERNAME')
    ELASTICSEARCH_PASSWORD = os.environ.get('ELASTICSEARCH_PASSWORD')
    ELASTICSEARCH_HTTP_AUTH = ('{}:{}'.format(ELASTICSEARCH_USERNAME,
                                              ELASTICSEARCH_PASSWORD)
                               if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
                               else None)
    ELASTICSEARCH_CHUNK_SIZE = int(os.environ.get('ELASTICSEARCH_CHUNK_SIZE', 100))

    # https://www.elastic.co/blog/index-vs-type

    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    USE_SENTRY = os.environ.get('USE_SENTRY') == "True"

    # Azure Settings
    USE_VOLUME_STORAGE = os.environ.get('USE_VOLUME_STORAGE') == "True"
    USE_AZURE_STORAGE = os.environ.get('USE_AZURE_STORAGE') == "True"
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    AZURE_STORAGE_CONTAINER = os.environ.get('AZURE_STORAGE_CONTAINER')
    AZURE_STORAGE_ACCOUNT_NAME = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
    AZURE_STORAGE_ACCOUNT_KEY = os.environ.get('AZURE_STORAGE_ACCOUNT_KEY')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    VIRUS_SCAN_ENABLED = os.environ.get('VIRUS_SCAN_ENABLED') == "True"
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 2525
    MAIL_USE_TLS = False
    MAIL_SUBJECT_PREFIX = '[OpenRecords Development]'
    MAIL_SENDER = 'OpenRecords - Dev Admin <donotreply@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
                               'postgresql://localhost:5432/openrecords_v2_0_dev')
    # Using Vagrant? Try: 'postgresql://vagrant@/openrecords_v2_0_dev'
    ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX') or "requests_dev"
    MAGIC_FILE = os.environ.get('MAGIC_FILE')


class TestingConfig(Config):
    LOGFILE_DIRECTORY = "/tmp/"
    TESTING = True
    WTF_CSRF_ENABLED = False  # TODO: retrieve and pass the token (via header or input value) for testing
    VIRUS_SCAN_ENABLED = True
    USE_SFTP = False
    UPLOAD_DIRECTORY = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data_test/')
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 2525
    MAIL_USE_TLS = False
    MAIL_SUBJECT_PREFIX = '[OpenRecords Testing]'
    MAIL_SENDER = 'OpenRecords - Pytest Admin <donotreply@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = 'postgresql://testuser@127.0.0.1:5432/openrecords_test'
    ELASTICSEARCH_INDEX = "requests_test"


class ProductionConfig(Config):
    VIRUS_SCAN_ENABLED = True
    ELASTICSEARCH_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
