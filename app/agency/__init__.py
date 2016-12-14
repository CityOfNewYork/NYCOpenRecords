from flask import Blueprint

agency = Blueprint('agency', __name__)

from . import views
