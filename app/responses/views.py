from app.responses import response_blueprint
from app.models import Requests
from flask import render_template


@response_blueprint.route('/<request_id>', methods=['GET', 'POST'])
def add_response(request_id):
    request = Requests.query.filter_by(id=request_id).first()
    if request:
        return render_template('request/view_request.html', request=request)