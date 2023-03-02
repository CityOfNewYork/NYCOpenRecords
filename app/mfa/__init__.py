from flask import Blueprint

mfa = Blueprint('mfa', __name__)

from . import views
