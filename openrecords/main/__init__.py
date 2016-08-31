from flask import Blueprint

main = Blueprint('main', __name__)

from flask import render_template, session, redirect, url_for, current_app

from app.main import views


