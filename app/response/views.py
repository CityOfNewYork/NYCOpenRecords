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
from app.response.utils import add_note, add_file, process_upload_data, send_response_email


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
    visibility = json.loads(current_request.visibility)
    form = NoteForm()
    if flask_request.method == 'POST':
        add_note(request_id=current_request.id,
                 content=form.note.data)
        flash('Note has been submitted')
    return render_template('request/view_note.html', request=current_request, form=form, visibility=visibility)


@response.route('/file/<request_id>', methods=['GET', 'POST'])
def response_file(request_id):
    """
    File response endpoint that takes in the metadata of a file for a specific request from the frontend.
    Calls process_upload_data to process the uploaded file form data.
    Passes data into helper function in response.utils to update changes into database.

    :param request_id: Specific FOIL request ID for the file
    :return: redirects to view request page as of right now (IN DEVELOPMENT)
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    visibility = json.loads(current_request.visibility)
    if flask_request.method == 'POST':
        files = process_upload_data(flask_request.form)
        for file in files:
            add_file(current_request.id,
                     file,
                     files[file]['title'],
                     files[file]['privacy'])

        private_files = []
        release_files = []
        for file in files:
            if files[file]['privacy'] == 'private':
                private_files.append(file)
            else:
                release_files.append(file)

        recipients_to_files = {
            "agency_only": private_files,
            "all": release_files
        }

        import ipdb
        ipdb.set_trace()
        # files_privacy = flask_request.form
        # for file in files_privacy:
        #     files_privacy = {}
        #     for key in files_privacy:
        #         if re_obj = re.compile(key):



        # email_content = flask_request.form['email-content']
        # send_response_email(current_request.id)
    return render_template('request/view_request.html', request=current_request, visibility=visibility)


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
