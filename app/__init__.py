from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from config import config
from business_calendar import Calendar, MO, TU, WE, TH, FR


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

UPLOAD_FOLDER = '/Desktop'
ALLOWED_EXTENSIONS = set(['txt', 'csv', 'jpeg'])


def create_app(config_name):
    """
    Set up the Flask Application context.

    :param config_name: Configuration for specific application context.

    :return: Flask application
    """
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    mail.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.request import request_blueprint
    app.register_blueprint(request_blueprint)

    # from .auth import auth as auth_blueprint
    # app.register_blueprint(auth_blueprint, url_prefix="/auth")

    return app
