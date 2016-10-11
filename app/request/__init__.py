from flask import Blueprint

request = Blueprint('request', __name__)

from . import views
