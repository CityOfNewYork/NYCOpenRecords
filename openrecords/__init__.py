from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
from os.path import abspath, dirname, join
from os import pardir, environ
from . import main
from business_calendar import Calendar, MO, TU, WE, TH, FR
db = SQLAlchemy()

app = Flask(__name__)


def create_app(config_name):
    """
    Set up the Flask Application context.

    :param config_name: Configuration for specific application context.

    :return: Flask application
    """
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .Auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    return app

