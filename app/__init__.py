from datetime import date

import redis
from business_calendar import Calendar, MO, TU, WE, TH, FR
from celery import Celery
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_kvsession import KVSessionExtension
from flask_elasticsearch import FlaskElasticsearch
from flask_login import LoginManager
from flask_mail import Mail
from flask_recaptcha import ReCaptcha
from flask_sqlalchemy import SQLAlchemy
from simplekv.decorator import PrefixDecorator
from simplekv.memory.redisstore import RedisStore
from app.lib import NYCHolidays, jinja_filters

from config import config, Config

recaptcha = ReCaptcha()
bootstrap = Bootstrap()
es = FlaskElasticsearch()
db = SQLAlchemy()
moment = Moment()
mail = Mail()
login_manager = LoginManager()
store = RedisStore(redis.StrictRedis(db=Config.SESSION_REDIS_DB, host=Config.REDIS_HOST, port=Config.REDIS_PORT))
prefixed_store = PrefixDecorator('session_', store)
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

upload_redis = redis.StrictRedis(db=Config.UPLOAD_REDIS_DB, host=Config.REDIS_HOST, port=Config.REDIS_PORT)
email_redis = redis.StrictRedis(db=Config.EMAIL_REDIS_DB, host=Config.REDIS_HOST, port=Config.REDIS_PORT)

holidays = NYCHolidays(years=[year for year in range(date.today().year, date.today().year + 5)])
calendar = Calendar(
    workdays=[MO, TU, WE, TH, FR],
    holidays=[str(key) for key in holidays.keys()]
)


def create_app(config_name):
    """
    Set up the Flask Application context.

    :param config_name: Configuration for specific application context.

    :return: Flask application
    """

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    app.jinja_env.filters['format_response_type'] = jinja_filters.format_response_type
    app.jinja_env.filters['format_response_privacy'] = jinja_filters.format_response_privacy
    app.jinja_env.filters['format_ultimate_determination_reason'] = jinja_filters.format_ultimate_determination_reason

    recaptcha.init_app(app)
    bootstrap.init_app(app)
    es.init_app(app, use_ssl=app.config['ELASTICSEARCH_USE_SSL'])
    db.init_app(app)
    moment.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    celery.conf.update(app.config)

    with app.app_context():
        from app.models import Anonymous
        login_manager.login_view = 'auth.login'
        login_manager.anonymous_user = Anonymous
        KVSessionExtension(prefixed_store, app)

    from .main import main
    app.register_blueprint(main)

    from .auth import auth
    app.register_blueprint(auth, url_prefix="/auth")

    from .request import request
    app.register_blueprint(request, url_prefix="/request")

    from .request.api import request_api_blueprint
    app.register_blueprint(request_api_blueprint, url_prefix="/request/api/v1.0")

    from .response import response
    app.register_blueprint(response, url_prefix="/response")

    from .upload import upload
    app.register_blueprint(upload, url_prefix="/upload")

    from .user import user
    app.register_blueprint(user, url_prefix="/user")

    from .search import search
    app.register_blueprint(search, url_prefix="/search")

    from .admin import admin
    app.register_blueprint(admin, url_prefix="/admin")

    return app
