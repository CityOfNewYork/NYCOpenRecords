from flask import Blueprint

agency_api_blueprint = Blueprint('agency_api_blueprint', __name__)

from . import views
