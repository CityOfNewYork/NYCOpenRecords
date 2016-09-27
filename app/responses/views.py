"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""

from app.responses import response_blueprint
from app.models import Requests
from flask import render_template, flash, request as flask_request, redirect, url_for
from flask_wtf import Form
from wtforms import StringField, SubmitField
from app.responses.utils import process_response
from app.constants import RESPONSE_TYPE


class NoteForm(Form):
    note = StringField('Add Note')
    submit = SubmitField('Submit')


@response_blueprint.route('/note/<request_id>', methods=['GET', 'POST'])
def add_response(request_id):
    request = Requests.query.filter_by(id=request_id).first().id
    form = NoteForm()
    if flask_request.method == 'POST':
        process_response(request_id=request, type=RESPONSE_TYPE['note'],
                         response_content=form.note.data)
        flash('Note has been submitted')
    return render_template('request/view_request.html', request=request, form=form)
