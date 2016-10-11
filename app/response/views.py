"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""

import json

from flask import render_template, flash, request as flask_request
from flask_wtf import Form
from wtforms import StringField, SubmitField

from app.models import Requests
from app.response import response
from app.response.utils import add_note, add_file
import os
from app import app


app.config['UPLOAD_FOLDER'] = '/Users/gzhou/PycharmProjects/openrecords_v2_0/data/FOIL-XXX'


# simple form used to test functionality of storing a note to responses table
class NoteForm(Form):
    note = StringField('Add Note')
    submit = SubmitField('Submit')


@response.route('/note/<request_id>', methods=['GET', 'POST'])
def response_note(request_id):
    request = Requests.query.filter_by(id=request_id).first().id
    form = NoteForm()
    if flask_request.method == 'POST':
        add_note(request_id=request,
                 content=form.note.data)
        flash('Note has been submitted')
    return render_template('request/view_note.html', request=request, form=form)


# TODO: Implement response route for file
@response.route('/file/<request_id>', methods=['GET', 'POST'])
def response_file(request_id):
    request = Requests.query.filter_by(id=request_id).first().id
    form = Submit()
    if flask_request.method == 'POST':
        # reads file from directory
        # currently commented out for loop for testing
        # for file in request.form.files:
            upload_file = os.path.join(app.config['UPLOAD_FOLDER'], 'OP-800.jpeg')
            add_file(request_id, upload_file)
            flash('File has been added')
    return render_template('request/view_request_test.html', request=request, form=form)


# TODO: Implement response route for extension
@response.route('/extension/<request_id>', methods=['GET', 'POST'])
def response_extension():
    pass


# TODO: Implement response route for email
@response.route('/email', methods=['GET', 'POST'])
def response_email():
    data = json.loads(flask_request.data.decode())
    request_id = data['request_id']
    return render_template('email_templates/email_file_upload.html',
                           department="Department of Records and Information Services",
                           page="http://127.0.0.1:5000/request/view/{}".format(request_id))


# TODO: Implement response route for sms
@response.route('/sms/<request_id>', methods=['GET', 'POST'])
def response_sms():
    pass


# TODO: Implement response route for push
@response.route('/push/<request_id>', methods=['GET', 'POST'])
def response_push():
    pass


# TODO: Implement response route for visiblity
@response.route('/visiblity/<request_id>', methods=['GET', 'POST'])
def response_visiblity():
    pass
