from flask import Blueprint

main = Blueprint('main', __name__, static_folder='static', static_url_path='/Users/atan/PycharmProjects/openrecords_v2_0/openrecords/static')

from flask import render_template, session, redirect, url_for, current_app
from . import main, views


