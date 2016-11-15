import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)


class Config:
    WTF_CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    LOGFILE_DIRECTORY = (os.environ.get('LOGFILE_DIRECTORY') or
                         os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logs/'))
    AGENCY_DATA = (os.environ.get('AGENCY_DATA') or
                   os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data'), 'agencies.csv'))

    # SAML Authentication Settings
    SAML_PATH = (os.environ.get('SAML_PATH') or
                os.path.join(os.path.abspath(os.path.dirname(__file__)), 'saml'))
    IDP = os.environ.get('IDP')

    # Database Settings
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    # Celery Settings
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'

    # Flask-Mail Settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = eval(str(os.environ.get('MAIL_USE_TLS'))) or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = os.environ.get('SUBJECT_PREFIX')
    MAIL_SENDER = os.environ.get('MAIL_SENDER')

    # Flask-SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # remove once this becomes the default

    # Upload Settings
    UPLOAD_QUARANTINE_DIRECTORY = (os.environ.get('UPLOAD_QUARANTINE_DIRECTORY') or
                                   os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quarantine/data/'))
    UPLOAD_DIRECTORY = (os.environ.get('UPLOAD_DIRECTORY') or
                        os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/'))
    VIRUS_SCAN_ENABLED = eval(str(os.environ.get('VIRUS_SCAN_ENABLED')))
    MAGIC_FILE = (os.environ.get('MAGIC_FILE') or
                  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'magic'))
    EMAIL_TEMPLATE_DIR = (os.environ.get('EMAIL_TEMPLATE_DIR') or 'email_templates/')

    # ReCaptcha
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

    # ElasticSearch settings
    ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST') or "localhost:9200"
    ELASTICSEARCH_ENABLED = eval(str(os.environ.get('ELASTICSEARCH_ENABLED'))) or True

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    VIRUS_SCAN_ENABLED = eval(str(os.environ.get('VIRUS_SCAN_ENABLED'))) or False
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 2500
    MAIL_USE_TLS = False
    MAIL_SUBJECT_PREFIX = '[OpenRecords Development]'
    MAIL_SENDER = 'OpenRecords - Dev Admin <donotreply@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
                               'postgresql://localhost:5432/openrecords_v2_0_dev')
    # Using Vagrant? Try: 'postgresql://vagrant@/openrecords_v2_0_dev'
    ELASTICSEARCH_ENABLED = eval(str(os.environ.get('ELASTICSEARCH_ENABLED')))
    MAGIC_FILE = eval(str(os.environ.get('MAGIC_FILE')))


class TestingConfig(Config):
    TESTING = True
    VIRUS_SCAN_ENABLED = True
    MAIL_SUBJECT_PREFIX = '[OpenRecords Testing]'
    MAIL_SENDER = 'OpenRecords - Testing Admin <donotreply@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = (os.environ.get('TEST_DATABASE_URL') or
                               'postgresql://localhost:5432/openrecords_v2_0_test')


class ProductionConfig(Config):
    VIRUS_SCAN_ENABLED = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
