from flask import Blueprint, session

main = Blueprint('main', __name__)

from . import views


@main.before_request
def func():
    session.modified = True
