"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""

import json

from flask import render_template, flash, request as flask_request, url_for, redirect
from flask_wtf import Form
from wtforms import StringField, SubmitField

from app.models import Requests
from app.response import response
from app.response.utils import add_note, add_file, add_extension,  process_upload_data, send_response_email, \
    process_privacy_options, process_email_template_request


# simple form used to test functionality of storing a note to responses table
class NoteForm(Form):
    note = StringField('Add Note')
    submit = SubmitField('Submit')


@response.route('/note/<request_id>', methods=['GET', 'POST'])
def response_note(request_id):
    """
    Note response endpoint that takes in the content of a note for a specific request from the frontend.
    Passes data into helper function in response.utils to update changes into database.

    :param request_id: Specific FOIL request ID for the note
    :return: Message indicating note has been submitted
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    form = NoteForm()
    if flask_request.method == 'POST':
        add_note(request_id=current_request.id,
                 content=form.note.data)
        flash('Note has been submitted')
    return render_template('request/view_note.html',
                           request=current_request,
                           form=form,
                           privacy=current_request.privacy)


@response.route('/file/<request_id>', methods=['POST'])
def response_file(request_id):
    """
    File response endpoint that takes in the metadata of a file for a specific request from the frontend.
    Calls process_upload_data to process the uploaded file form data.
    Passes data into helper function in response.utils to update changes into database.

    :param request_id: Specific FOIL request ID for the file
    :return: redirects to view request page as of right now (IN DEVELOPMENT)
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    if flask_request.method == 'POST':
        files = process_upload_data(flask_request.form)
        for file_data in files:
            add_file(current_request.id,
                     file_data,
                     files[file_data]['title'],
                     files[file_data]['privacy'])
        file_options = process_privacy_options(files)
        email_content = flask_request.form['email-content']
        for privacy, files in file_options.items():
            send_response_email(request_id, privacy, files, email_content)
    return redirect(url_for('request.view', request_id=request_id))


# TODO: Implement response route for extension
@response.route('/extension/<request_id>', methods=['GET', 'POST'])
def response_extension(request_id):
    stuff = flask_request.form
    add_extension(request_id, stuff)
    return redirect(url_for('request.view', request_id=request_id))


# TODO: Implement response route for email
@response.route('/email', methods=['GET', 'POST'])
def response_email():
    """
    Currently renders the template of the email onto the add file form.

    :return: Render email template to add file form
    """
    data = json.loads(flask_request.data.decode())
    request_id = data['request_id']
    email_template = process_email_template_request(data, request_id)
    return email_template


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
