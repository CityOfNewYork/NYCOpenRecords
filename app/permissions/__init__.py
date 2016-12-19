from flask import Blueprint

permissions = Blueprint('permissions', __name__)

from . import views
