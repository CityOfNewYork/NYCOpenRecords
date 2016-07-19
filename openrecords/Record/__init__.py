from flask import Blueprint

record = Blueprint('Record', __name__)

from . import views