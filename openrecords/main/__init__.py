from flask import Blueprint

main = Blueprint('main', __name__)

from . import views

from flask import render_template, session, redirect, url_for, current_app
from . import main, views
#from .forms import <FORM NAME HERE>

