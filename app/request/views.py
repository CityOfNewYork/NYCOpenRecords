"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""

from flask import (
    render_template,
    request,
    redirect,
    url_for,
)
from app.request.forms import NewRequestForm
from app.request import request_blueprint
from app.request.utils import process_request
from app import app
from werkzeug.utils import secure_filename
import os
from constants import ALLOWED_EXTENSIONS


# def allowed_filename(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


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
            process_request(title=form.request_title.data, description=form.request_description.data,
                            submission=form.request_submission.data)
            submitted_file = secure_filename(form.request_file.data)
            form.request_file.data.save('app/static/' + submitted_file)
            # submitted_file = form.request_file
            # if submitted_file:
            #     filename = secure_filename(submitted_file.data)

            return redirect(url_for('main.index'))

        else:
            print(form.errors)
    return render_template('request/new_request.html', form=form)
