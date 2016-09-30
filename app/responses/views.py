"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""

from app.responses import response
from app.models import Requests
from flask import render_template, flash, request as flask_request
from flask_wtf import Form
from wtforms import StringField, SubmitField
from app.responses.utils import add_note, add_file
import os
from app import app


app.config['UPLOAD_FOLDER'] = '/Users/gzhou/PycharmProjects/openrecords_v2_0/data/FOIL-XXX'


def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """

    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i = i + 1

    return filename


# simple form used to test functionality of storing a note to responses table
class NoteForm(Form):
    note = StringField('Add Note')
    submit = SubmitField('Submit')


# submit botton to test functionality of storing a file to responses table
class Submit(Form):
    submit_file = SubmitField('Add File')


@response.route('/note/<request_id>', methods=['GET', 'POST'])
def response_note(request_id):
    request = Requests.query.filter_by(id=request_id).first().id
    form = NoteForm()
    if flask_request.method == 'POST':
        add_note(request_id=request,
                 content=form.note.data)
        flash('Note has been submitted')
    return render_template('request/view_request.html', request=request, form=form)


# TODO: Implement response route for file
@response.route('/file/<request_id>', methods=['GET', 'POST'])
def response_file(request_id):
    request = Requests.query.filter_by(id=request_id).first().id
    form = Submit()
    if flask_request.method == 'POST':
        # reads file from directory
        gen_file_name(filename)
        upload_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        add_file(request_id, upload_file)
        flash('File has been added')
    return render_template('request/view_request.html', request=request, form=form)


# TODO: Implement response route for extension
@response.route('/extension/<request_id>', methods=['GET', 'POST'])
def response_extension():
    pass


# TODO: Implement response route for email
@response.route('/email/<request_id>', methods=['GET', 'POST'])
def response_email():
    pass


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
