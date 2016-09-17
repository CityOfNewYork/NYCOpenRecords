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
from werkzeug.utils import secure_filename


@request_blueprint.route('/new', methods=['GET', 'POST'])
def new_request():
    """
    Create a new FOIL request

    title: request title
    description: request description
    agency: agency selected for the request
    submission: submission method for the request

    :return: redirects to homepage if form validates
     uploaded file is stored in app/static
     if form fields are missing or has improper values, backend error messages (WTForms) will appear
    """
    form = NewRequestForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            # Helper function to handle processing of data and secondary validation on the backend
            process_request(title=form.request_title.data, description=form.request_description.data,
                            submission=form.request_submission.data)
            # File upload that stores uploaded file to app/static
            filename = secure_filename(form.request_file.data.filename)
            form.request_file.data.save('app/static/' + filename)
            return redirect(url_for('main.index'))
        else:
            print(form.errors)
    return render_template('request/new_request.html', form=form)
