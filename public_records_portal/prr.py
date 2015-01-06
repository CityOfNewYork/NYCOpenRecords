"""
    public_records_portal.prr
    ~~~~~~~~~~~~~~~~

    Implements functions specific to managing or creating a public records request.

"""

from public_records_portal import app, db_helpers
import os, time, json
from flask import Flask, request
from flask.ext.login import current_user
from datetime import datetime, timedelta
from db_helpers import find_request, create_request, get_obj, add_staff_participant, remove_staff_participant, update_obj, get_attribute, change_request_status, create_or_return_user, create_subscriber, create_record, create_note, create_QA, create_answer, update_user
from models import *
from ResponsePresenter import ResponsePresenter
from RequestPresenter import RequestPresenter
from notifications import generate_prr_emails
import scribd_helpers
from spam import is_spam
import logging
import csv
import urllib

### @export "add_resource"
def add_resource(resource, request_body, current_user_id = None):
	fields = request_body
	if "extension" in resource:
		return request_extension(int(fields['request_id']), fields.getlist('extend_reason'), current_user_id)
	if "note" in resource:
		return add_note(request_id = int(fields['request_id']), text = fields['note_text'], user_id = current_user_id, passed_spam_filter = True) # Bypass spam filter because they are logged in.
	elif "record" in resource:
		if fields['record_description'] == "":
			return "When uploading a record, please fill out the 'summary' field."
		if 'record_access' in fields and fields['record_access'] != "":
			return add_offline_record(int(fields['request_id']), fields['record_description'], fields['record_access'], current_user_id)
		elif 'link_url' in fields and fields['link_url'] != "":
			return add_link(request_id = int(fields['request_id']), url = fields['link_url'], description = fields['record_description'], user_id = current_user_id)
		else:
			document = None
			try:
				document = request.files['record']
			except:
				app.logger.info("\n\nNo file passed in")
			return upload_record(request_id = int(fields['request_id']), document = document, description = fields['record_description'], user_id = current_user_id)
	elif "qa" in resource:
		return ask_a_question(request_id = int(fields['request_id']), user_id = current_user_id, question = fields['question_text'])
	elif "owner" in resource:
		participant_id, new = add_staff_participant(request_id = fields['request_id'], email = fields['owner_email'], reason = fields['owner_reason'])
		if new:
			generate_prr_emails(request_id = fields['request_id'], notification_type = "Staff participant added", user_id = get_attribute("user_id", obj_id = participant_id, obj_type = "Owner"))
		return participant_id
	elif "subscriber" in resource:
		return add_subscriber(request_id=fields['request_id'], email = fields['follow_email'])
	else:
		return False

### @export "update_resource"
def update_resource(resource, request_body):
	fields = request_body
	if "owner" in resource:
		if "reason_unassigned" in fields:
			return remove_staff_participant(owner_id = fields['owner_id'], reason = fields['reason_unassigned'])
		else:
			change_request_status(int(fields['request_id']), "Rerouted")
			return assign_owner(int(fields['request_id']), fields['owner_reason'], fields['owner_email'])
	elif "reopen" in resource:
		change_request_status(int(fields['request_id']), "Reopened")
		return fields['request_id']
	elif "request_text" in resource:
		update_obj(attribute = "text", val = fields['request_text'], obj_type = "Request", obj_id = fields['request_id'])
	elif "note_text" in resource:
		update_obj(attribute = "text", val = fields['note_text'], obj_type = "Note", obj_id = fields['response_id'])
		# Need to store note text somewhere else (or just do delete here as well)
	elif "note_delete" in resource:
		# Need to store note somewhere else
		remove_obj("Note", int(fields['response_id']))
	elif "record_delete" in resource:
		remove_obj("Record", int(fields['record_id']))
		# Need to store record somewhere else and prompt them to delete from Scribd as well, if they'd like
	else:
		return False

### @export "request_extension"
def request_extension(request_id, extension_reasons, user_id):
	req = Request.query.get(request_id)
	req.extension()
	text = "Request extended:"
	for reason in extension_reasons:
		text = text + reason + "</br>"
	add_staff_participant(request_id = request_id, user_id = user_id)
	return add_note(request_id = request_id, text = text, user_id = user_id, passed_spam_filter = True) # Bypass spam filter because they are logged in.

### @export "add_note"
def add_note(request_id, text, user_id = None, passed_spam_filter = False):
	if not text or text == "" or (not passed_spam_filter):
		return False
	note_id = create_note(request_id = request_id, text = text, user_id = user_id)
	if note_id:
		change_request_status(request_id, "A response has been added.")
		if user_id:
			add_staff_participant(request_id = request_id, user_id = user_id)
			generate_prr_emails(request_id = request_id, notification_type = "City response added")
		else:
			generate_prr_emails(request_id = request_id, notification_type = "Public note added")
		return note_id
	return False



### @export "upload_record"
def upload_record(request_id, description, user_id, document = None):
	""" Creates a record with upload/download attributes """
	try:
		doc_id, filename = scribd_helpers.upload_file(document = document, request_id = request_id)
	except:
		return "The upload timed out, please try again."
	if doc_id == False:
		return "Extension type '%s' is not allowed." % filename
	else:
		if str(doc_id).isdigit():
			record_id = create_record(doc_id = doc_id, request_id = request_id, user_id = user_id, description = description, filename = filename, url = app.config['HOST_URL'] + doc_id)
			change_request_status(request_id, "A response has been added.")
			generate_prr_emails(request_id = request_id, notification_type = "City response added")
			add_staff_participant(request_id = request_id, user_id = user_id)
			return record_id
	return "There was an issue with your upload."

### @export "add_offline_record"
def add_offline_record(request_id, description, access, user_id):
	""" Creates a record with offline attributes """
	record_id = create_record(request_id = request_id, user_id = user_id, access = access, description = description) # To create an offline record, we need to know the request ID to which it will be added, the user ID for the person adding the record, how it can be accessed, and a description/title of the record.
	if record_id:
		change_request_status(request_id, "A response has been added.")
		generate_prr_emails(request_id = request_id, notification_type = "City response added")
		add_staff_participant(request_id = request_id, user_id = user_id)
		return record_id
	return False

### @export "add_link"
def add_link(request_id, url, description, user_id):
	""" Creates a record with link attributes """
	record_id = create_record(url = url, request_id = request_id, user_id = user_id, description = description)
	if record_id:
		change_request_status(request_id, "A response has been added.")
		generate_prr_emails(request_id = request_id, notification_type = "City response added")
		add_staff_participant(request_id = request_id, user_id = user_id)
		return record_id
	return False

### @export "make_request"			
def make_request(text, email = None, user_id = None, phone = None, alias = None, department = None, passed_spam_filter = False, offline_submission_type = None, date_received = None):
	""" Make the request. At minimum you need to communicate which record(s) you want, probably with some text."""
	if not passed_spam_filter: 
		return None, False
	request_id = find_request(text)
	if request_id: # Same request already exists
		return request_id, False
	assigned_to_email = app.config['DEFAULT_OWNER_EMAIL']
	assigned_to_reason = app.config['DEFAULT_OWNER_REASON']
	if department:
		app.logger.info("\n\nDepartment chosen: %s" %department)
		prr_email = db_helpers.get_contact_by_dept(department)
		if prr_email:
			assigned_to_email = prr_email
			assigned_to_reason = "PRR Liaison for %s" %(department)
		else:
			app.logger.info("%s is not a valid department" %(department))
			department = None
	request_id = create_request(text = text, user_id = user_id, offline_submission_type = offline_submission_type, date_received = date_received) # Actually create the Request object
	new_owner_id = assign_owner(request_id = request_id, reason = assigned_to_reason, email = assigned_to_email) # Assign someone to the request
	open_request(request_id) # Set the status of the incoming request to "Open"
	if email or alias or phone:
		subscriber_user_id = create_or_return_user(email = email, alias = alias, phone = phone)
		subscriber_id, is_new_subscriber = create_subscriber(request_id = request_id, user_id = subscriber_user_id)
		if subscriber_id:
			generate_prr_emails(request_id, notification_type = "Request made", user_id = subscriber_user_id) # Send them an e-mail notification
	return request_id, True

### @export "add_subscriber"	
def add_subscriber(request_id, email):
	user_id = create_or_return_user(email = email)
	subscriber_id, is_new_subscriber = create_subscriber(request_id = request_id, user_id = user_id)
	if subscriber_id:
		generate_prr_emails(request_id, notification_type = "Request followed", user_id = user_id)
		return subscriber_id
	return False

### @export "ask_a_question"	
def ask_a_question(request_id, user_id, question):
	""" City staff can ask a question about a request they are confused about."""
	req = get_obj("Request", request_id)
	qa_id = create_QA(request_id = request_id, question = question, user_id = user_id)
	if qa_id:
		change_request_status(request_id, "Pending")
		requester = req.requester()
		if requester:
			generate_prr_emails(request_id, notification_type = "Question asked", user_id = requester.user_id)
		add_staff_participant(request_id = request_id, user_id = user_id)
		return qa_id
	return False

### @export "answer_a_question"
def answer_a_question(qa_id, answer, subscriber_id = None, passed_spam_filter = False):
	""" A requester can answer a question city staff asked them about their request."""
	if (not answer) or (answer == "") or (not passed_spam_filter):
		return False
	else:
		request_id = create_answer(qa_id, subscriber_id, answer)
		# We aren't changing the request status if someone's answered a question anymore, but we could change_request_status(request_id, "Pending")
		generate_prr_emails(request_id = request_id, notification_type = "Question answered")
		return True

### @export "open_request"	
def open_request(request_id):
	change_request_status(request_id, "Open")

### @export "assign_owner"	
def assign_owner(request_id, reason, email = None): 
	""" Called any time a new owner is assigned. This will overwrite the current owner."""
	req = get_obj("Request", request_id)
	past_owner_id = None
	# If there is already an owner, unassign them:
	if req.point_person():
		past_owner_id = req.point_person().id
		past_owner = get_obj("Owner", req.point_person().id)
		update_obj(attribute = "is_point_person", val = False, obj = past_owner)
	owner_id, is_new_owner = add_staff_participant(request_id = request_id, reason = reason, email = email, is_point_person = True)
	if (past_owner_id == owner_id): # Already the current owner, so don't send any e-mails
		return owner_id

	app.logger.info("\n\nA new owner has been assigned: Owner: %s" % owner_id)
	new_owner = get_obj("Owner", owner_id)	
	# Update the associated department on request
	update_obj(attribute = "department_id", val = new_owner.user.department, obj = req)
	user_id = get_attribute(attribute = "user_id", obj_id = owner_id, obj_type = "Owner")
	# Send notifications
	if is_new_owner:
		generate_prr_emails(request_id = request_id, notification_type = "Request assigned", user_id = user_id)
	return owner_id

### @export "get_request_data_chronologically"
def get_request_data_chronologically(req):
	public = False
	if current_user.is_anonymous():
		public = True
	responses = []
	if not req:
		return responses
	for i, note in enumerate(req.notes):
		if not note.user_id:
			responses.append(RequestPresenter(note = note, index = i, public = public, request = req))
	for i, qa in enumerate(req.qas):
		responses.append(RequestPresenter(qa = qa, index = i, public = public, request = req))
	if not responses:
		return responses
	responses.sort(key = lambda x:x.date(), reverse = True)
	return responses

### @export "get_responses_chronologically"
def get_responses_chronologically(req):
	responses = []
	if not req:
		return responses
	for note in req.notes:
		if note.user_id:
			responses.append(ResponsePresenter(note = note))
	for record in req.records:
		responses.append(ResponsePresenter(record = record))
	if not responses:
		return responses
	responses.sort(key = lambda x:x.date(), reverse = True)
	if "Closed" in req.status:
		responses[0].set_icon("icon-archive") # Set most recent note (closed note)'s icon
	return responses

### @export "set_directory_fields"
def set_directory_fields():
	# Set basic user data
	if 'STAFF_URL' in app.config:
		# This gets run at regular internals via db_users.py in order to keep the staff user list up to date. Before users are added/updated, ALL users get reset to 'inactive', and then only the ones in the current CSV are set to active. 
		for user in User.query.filter(User.is_staff == True).all():
			update_user(user = user, is_staff = False)
		csvfile = urllib.urlopen(app.config['STAFF_URL'])
		dictreader = csv.DictReader(csvfile, delimiter=',')
		for row in dictreader:
			create_or_return_user(email = row['email'].lower(), alias = row['name'], phone = row['phone number'], department = row['department name'], is_staff = True)
		# Set liaisons data (who is a PRR liaison for what department)
		if 'LIAISONS_URL' in app.config:
			csvfile = urllib.urlopen(app.config['LIAISONS_URL'])
			dictreader = csv.DictReader(csvfile, delimiter=',')
			for row in dictreader:
				user = create_or_return_user(email = row['PRR liaison'], contact_for = row['department name'])
				if row['PRR backup'] != "":
					user = create_or_return_user(email = row['PRR backup'], backup_for = row['department name'])
		else:
			app.logger.info("\n\n Please update the config variable LIAISONS_URL for where to find department liaison data for your agency.")
	else:
		app.logger.info("\n\n Please update the config variable STAFF_URL for where to find csv data on the users in your agency.") 
		if 'DEFAULT_OWNER_EMAIL' in app.config and 'DEFAULT_OWNER_REASON' in app.config:
			create_or_return_user(email = app.config['DEFAULT_OWNER_EMAIL'].lower(), alias = app.config['DEFAULT_OWNER_EMAIL'], department = app.config['DEFAULT_OWNER_REASON'], is_staff = True)
			app.logger.info("\n\n Creating a single user from DEFAULT_OWNER_EMAIL and DEFAULT_OWNER_REASON for now. You may log in with %s" %(app.config['DEFAULT_OWNER_EMAIL']))
		else:
			app.logger.info("\n\n Unable to create any users. No one will be able to log in.")



### @export "close_request"
def close_request(request_id, reason = "", user_id = None):
	req = get_obj("Request", request_id)
	change_request_status(request_id, "Closed")
	# Create a note to capture closed information:
	create_note(request_id, reason, user_id)
	generate_prr_emails(request_id = request_id, notification_type = "Request closed")
	add_staff_participant(request_id = request_id, user_id = user_id)
