from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
from os.path import abspath, dirname, join
from os import pardir, environ
from . import main
from business_calendar import Calendar, MO, TU, WE, TH, FR
import time, os, logging
from logging import Formatter
from logging.handlers import RotatingFileHandler
from flask_bootstrap import Bootstrap

db = SQLAlchemy()
bootstrap = Bootstrap()
app = Flask(__name__, static_folder='./static')


def create_app(config_name):
    """
    Set up the Flask Application context.

    :param config_name: Configuration for specific application context.

    :return: Flask application
    """
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    db.init_app(app)
    bootstrap.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .Auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    from .Home import home as home_blueprint
    app.register_blueprint(home_blueprint, url_prefix="/home")

    logfile_name = "openrecords_" + \
                   time.strftime("%Y-%m-%d_%H:%M:%S") + \
                   ".log"
    handler = RotatingFileHandler(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'log'), logfile_name), maxBytes=10000, backupCount=1)
    handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s '
                                   '[in %(pathname)s:%(lineno)d]'))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    return app

