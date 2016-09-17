from business_calendar import Calendar, MO, TU, WE, TH, FR
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

from config import config

bootstrap = Bootstrap()
db = SQLAlchemy()
mail = Mail()
app = Flask(__name__)

calendar = Calendar(
    workdays=[MO, TU, WE, TH, FR],
    holidays=[
        '2016-01-01',
        '2016-01-18',
        '2016-02-15',
        '2016-05-30',
        '2016-07-4',
        '2016-09-5',
        '2016-10-10',
        '2016-11-08',
        '2016-11-11',
        '2016-11-24',
        '2016-12-26'
    ]
)


def create_app(config_name):
    """
    Set up the Flask Application context.

    :param config_name: Configuration for specific application context.

    :return: Flask application
    """
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    db.init_app(app)
    mail.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.request import request_blueprint
    app.register_blueprint(request_blueprint)

    return app
