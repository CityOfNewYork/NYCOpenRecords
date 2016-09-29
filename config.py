import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)


class Config:
    WTF_CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SAML_PATH = os.environ.get('SAML_PATH') or os.path.join(os.path.abspath(os.curdir), 'saml')
    AGENCY_DATA = os.environ.get('AGENCY_DATA') or os.path.join(os.path.join(os.path.abspath(os.curdir), 'data'),
                                                                'agencies.csv')
    IDP = os.environ.get('IDP')
    LOGFILE_DIRECTORY = os.environ.get('LOGFILE_DIRECTORY') or os.path.join(os.path.abspath(os.curdir), 'logs/')
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = os.environ.get('[SUBJECT_PREFIX]')
    MAIL_SENDER = os.environ.get('[MAIL_SENDER]')
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    UPLOAD_QUARANTINE_DIRECTORY = os.path.join(os.path.abspath(os.curdir), 'quarantine/data/')
    UPLOAD_DIRECTORY = os.path.join(os.path.abspath(os.curdir), 'data/')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = 2500
    MAIL_USE_TLS = False
    MAIL_SUBJECT_PREFIX = os.environ.get('[SUBJECT_PREFIX]') or 'OpenRecords'
    MAIL_SENDER = os.environ.get('[MAIL_SENDER]') or 'Records Admin <openrecords@records.nyc.gov>'
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
                              'postgresql://localhost:5432/openrecords_v2_0_dev')
    # Using Vagrant? Try: 'postgresql://vagrant@/openrecords_v2_0_dev'


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
