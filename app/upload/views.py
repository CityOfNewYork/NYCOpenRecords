from app import api
from flask import request
from flask.ext.restplus import Resource, reqparse, fields
from werkzeug.datastructures import FileStorage

ns = api.namespace('upload', description='Upload operations for Responses')

upload = api.model('Upload' {
    'request_id': fields.String(readOnly=True, description='Request Unique Identifier'),
    'resource_id': fields.Integer(description='Resource Unique Identifier'),
    'file': fields.FileStorage(required=True)
})
