from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
from . import main

db = SQLAlchemy()


def create_app(config_name):
    """
    Set up the Flask Application context.

    :param config_name: Configuration for specific application context.

    :return: Flask application
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    return app

