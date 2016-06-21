from flask import Blueprint

home = Blueprint('Request', __name__)

from . import views