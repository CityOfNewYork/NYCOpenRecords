from flask import Blueprint

help = Blueprint('Help', __name__)

from . import views