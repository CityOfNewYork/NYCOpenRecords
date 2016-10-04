from flask import Blueprint

response = Blueprint('response', __name__)

from . import views
