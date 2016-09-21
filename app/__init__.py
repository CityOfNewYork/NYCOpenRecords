import redis
from flask import Flask
from flask_kvsession import KVSessionExtension
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from simplekv.decorator import PrefixDecorator
from simplekv.memory.redisstore import RedisStore

from config import config

db = SQLAlchemy()
login_manager = LoginManager()
store = RedisStore(redis.StrictRedis(db=1))
prefixed_store = PrefixDecorator('session_', store)

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
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    KVSessionExtension(prefixed_store, app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    return app
