from flask import Blueprint

request_blueprint = Blueprint('request_blueprint', __name__, url_prefix='/request')

from . import views