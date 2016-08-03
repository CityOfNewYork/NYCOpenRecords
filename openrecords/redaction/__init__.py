from flask import Blueprint

redaction = Blueprint('Redaction', __name__)

from . import views