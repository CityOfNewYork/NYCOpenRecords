from flask import Blueprint

home = Blueprint('Home', __name__)

from . import views