"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""

from app.response import response
from app.models import Requests
from flask import render_template, flash, request as flask_request
from flask_wtf import Form
from wtforms import StringField, SubmitField
from app.response.utils import add_note


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
    return render_template('request/view_request.html', request=request, form=form)


# TODO: Implement response route for file
@response.route('/file/<request_id>', methods=['GET', 'POST'])
def response_file():
    pass


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
