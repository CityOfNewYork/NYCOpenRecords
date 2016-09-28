import redis
from business_calendar import Calendar, MO, TU, WE, TH, FR
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_kvsession import KVSessionExtension
from flask_login import LoginManager
from flask_mail import Mail
from business_calendar import Calendar, MO, TU, WE, TH, FR
from flask_sqlalchemy import SQLAlchemy
from simplekv.decorator import PrefixDecorator
from simplekv.memory.redisstore import RedisStore
from celery import Celery

from config import config, Config

bootstrap = Bootstrap()
db = SQLAlchemy()
login_manager = LoginManager()
store = RedisStore(redis.StrictRedis(db=1))
prefixed_store = PrefixDecorator('session_', store)
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

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
    login_manager.init_app(app)
    mail.init_app(app)
    celery.conf.update(app.config)

    with app.app_context():
        db.create_all(app=app)

        from app.models import Anonymous

        login_manager.login_view = 'auth.login'
        login_manager.anonymous_user = Anonymous
        KVSessionExtension(prefixed_store, app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    from .request import request_blueprint
    app.register_blueprint(request_blueprint)

    from .responses import response as response_blueprint
    app.register_blueprint(response_blueprint, url_prefix='/response')
    return app
