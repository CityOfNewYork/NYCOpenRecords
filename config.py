import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'SECRET KEY'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 1111
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = '[TimeClock]'
    MAIL_SENDER = 'Records Timeclock <RTimeclock@records.nyc.gov>'
    WTF_CSRF_ENABLED = True

    # Asset Paths
    NYC_GOV_BASE = os.environ.get('NYC_GOV_BASE') or 'http://www1.nyc.gov/'

    # SAML Keys
    SAML_PATH = os.environ.get('SAML_PATH') or os.path.join(os.path.abspath(os.curdir), 'saml')

    # Logging
    LOGFILE_DIRECTORY = os.environ.get('LOGFILE_DIRECTORY') or os.path.join(os.path.pardir, 'logs')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://localhost:5432/openrecords_v2_0_dev'
    NYC_GOV_BASE = 'http://nyc-stg-web.csc.nycnet/'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://localhost:5432/openrecords_v2_0_dev'
    NYC_GOV_BASE = 'http://nyc-stg-web.csc.nycnet/'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://localhost:5432/openrecords_v2_0_dev'
    NYC_GOV_BASE = 'http://www1.nyc.gov/'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
