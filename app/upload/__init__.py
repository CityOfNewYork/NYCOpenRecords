from flask import Blueprint, session

upload = Blueprint('upload', __name__, url_prefix='/upload')

from . import views
