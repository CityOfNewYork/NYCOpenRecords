from flask import Blueprint

request_api_blueprint = Blueprint('request_api_blueprint', __name__)

from . import views
