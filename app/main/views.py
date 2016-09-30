"""
.. module:: main.views.

   :synopsis: Handles all core URL endpoints for the timeclock application
"""

from datetime import datetime
from flask import current_app
from flask import (
    render_template,
    flash,
    request,
    make_response,
    url_for,
    redirect,
    session
)

from app.models import Users
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('base.html')

@main.route('/status', methods=['GET'])
def status():
    return render_template('request/status.html')
