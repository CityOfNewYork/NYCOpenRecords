from flask import Blueprint

request = Blueprint('Request', __name__)

from . import views