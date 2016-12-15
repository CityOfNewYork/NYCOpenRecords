from flask import Blueprint

user_request = Blueprint('user_request', __name__)

from . import views
