"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    Flask
)
from datetime import datetime
from .. import db
from .. models import Request
from . forms import NewRequestForm
from . import request_blueprint
import random
import string
import os
from .. db_helpers import create_request


@request_blueprint.route('/new', methods=['GET', 'POST'])
def new_request():
    """
    Create a new FOIL request

    1) What are the inputs (from the Request Form)
    2) What are the expected values for each of the above
    3) What are the valid returns from this function (errors, success, messages)
    4) Anything else we need to know

    """
    form = NewRequestForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(id=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)),
                title=form.request_title.data, description=form.request_description.data, date_created=datetime.now())
            # newrequest = Request(id=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)),
            #                      title=form.request_title.data, description=form.request_description.data,
            #                      date_created=datetime.now()
            #                      )
            # db.session.add(newrequest)
            # db.session.commit()
            return redirect(url_for('main.index'))

        else:
            print(form.errors)
    return render_template('request/new_request.html', form=form)
