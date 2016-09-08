import logging
import os
import time
from datetime import timedelta
from logging import Formatter
from logging.handlers import RotatingFileHandler

from flask import Flask, session
from flask_kvsession import KVSessionExtension
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from simplekv.db.sql import SQLAlchemyStore

from config import config

migrate = Migrate()
db = SQLAlchemy()


def load_db(db):
    db.create_all()


def create_app(config_name):  # App Factory
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if os.environ.get('DATABASE_URL') is None:
        app.config[
            'SQLALCHEMY_DATABASE_URI'] = \
            app.config.get('SQLALCHEMY_DATABASE_URI')
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

    config[config_name].init_app(app)
    migrate.init_app(app, db)
    db.init_app(app)
    with app.app_context():
        load_db(db)
        store = SQLAlchemyStore(db.engine, db.metadata, 'sessions')
        kvsession = KVSessionExtension(store, app)
        logfile_name = "{}/{}.log".format(app.config['LOGFILE_DIRECTORY'], time.strftime("%Y%m%d-%H%M%S"))
        handler = RotatingFileHandler(logfile_name, maxBytes=10000, backupCount=1)
        handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s '
                                       '[in %(pathname)s:%(lineno)d]'))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    app.permanent_session_lifetime = timedelta(minutes=15)

    @app.before_request
    def func():
        session.modified = True

    return app
