from flask import Blueprint

request_blueprint = Blueprint('request_blueprint', __name__)

from . import views