from flask import Blueprint

response_blueprint = Blueprint('response_blueprint', __name__, url_prefix='/response')

from . import views