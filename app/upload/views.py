"""
...module:: upload.views.

    :synopsis: Handles Upload endpoints for NYC OpenRecords
"""
import os
from flask import (
    request,
    jsonify,
    render_template,
    current_app,
)
from werkzeug.utils import secure_filename
from . import upload
from .utils import (
    parse_content_range,
    is_valid_file_type,
    scan_and_complete_upload
)
from .constants import CONTENT_RANGE_HEADER


@upload.route('/<request_id>', methods=['POST'])
def post(request_id):
    """
    Create a new upload.

    Handles chunked files through the Content-Range header.
    For filesize validation and more upload logic, see:
        /static/js/plugins/jquery.fileupload-main.js

    :returns: {
        "name": file name,
        "size": file size
    }
    """
    files = request.files
    file_ = files[next(files.keys())]
    filename = secure_filename(file_.filename)
    upload_path = os.path.join(
        current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
        request_id)
    if not os.path.exists(upload_path):
        os.mkdir(upload_path)
    filepath = os.path.join(upload_path, filename)

    try:
        if CONTENT_RANGE_HEADER in request.headers:
            start, size = parse_content_range(
                request.headers[CONTENT_RANGE_HEADER])

            # Only validate mime type on first chunk
            valid_file_type = True
            file_type = None
            if start == 0:
                valid_file_type, file_type = is_valid_file_type(file_)

            if valid_file_type:
                with open(filepath, 'ab') as fp:
                    fp.seek(start)
                    fp.write(file_.stream.read())
                # scan if last chunk written
                if os.path.getsize(filepath) == size:
                    scan_and_complete_upload.delay(request_id, filepath)
        else:
            valid_file_type, file_type = is_valid_file_type(file_)
            if valid_file_type:
                file_.save(filepath)
                scan_and_complete_upload.delay(request_id, filepath)

        if not valid_file_type:
            response = {
                "files": [{
                    "name": filename,
                    "error": "File type '{}' is not allowed.".format(file_type)
                }]
            }
        else:
            response = {
                "files": [{
                    "name": filename,
                    "size": os.path.getsize(filepath),
                    # "url": filepath,
                    # "deleteUrl": filepath,
                    # "deleteType": 'DELETE',
                }]
            }

    except Exception as e:
        print("Upload for file '{}' failed: {}".format(filename, e))
        response = {
            "files": [{
                "name": filename,
                "error": "Error uploading file."
            }]
        }

    return jsonify(response), 200


@upload.route('/<request_id>', methods=['GET'])
def get(request_id):
    return jsonify({}), 200


@upload.route('/test', methods=['GET'])
def test():
    return render_template('upload/uploads.html')


@upload.route('/status/<request_id>', methods=['GET'])
def status(request_id):
    # check redis
    # get_redis_key_upload(request_id, filename)
    return jsonify({}), 200
