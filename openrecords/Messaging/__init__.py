from flask import Blueprint

messaging = Blueprint('Messaging', __name__)

from . import views