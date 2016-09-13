"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""

from flask import Flask, abort, request
from flask_restful import Api, Resource, reqparse, fields, marshal
from . import request_blueprint

api = Api(request_blueprint)

requests = [
    {
        'id': 1,
        'title': u'Birth Certificate',
        'description': u'Birth Certificate for myself',
        'agency': 2,
        'submission': u'Phone'
    },
    {
        'id': 2,
        'title': u'Email Records',
        'description': u'Email Records from the agency',
        'agency': 3,
        'submission': u'Online'
    }
]

request_fields = {
    'title': fields.String,
    'description': fields.String,
    'agency': fields.Integer,
    'submission': fields.String,
    'uri': fields.Url('request')
}


# def abort_if_request_doesnt_exist(request_id):
#     if request_id not in requests:
#         abort(404, message="Request {} doesn't exist".format(request_id))


class RequestAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('title', type=str, required=True,
                                   help='No request title provided',
                                   location='json')
        self.reqparse.add_argument('description', type=str, default="", location='json')
        self.reqparse.add_argument('agency', type=int, default="", location='json')
        self.reqparse.add_argument('submission', type=str, default="", location='json')
        self.reqparse.add_argument('uri', type=str, default="", location=request.url)
        super(RequestAPI, self).__init__()

    def post(self):
        args = self.reqparse.parse_args()
        # request = {
        #     'id': requests[-1]['id'] + 1,
        #     'title': args['title'],
        #     'description': args['description'],
        #     'submission': args['submission']
        # }
        requests.append(request)

        request.json['uri'] = request.url
        return request.json

api.add_resource(RequestAPI, '/request')

