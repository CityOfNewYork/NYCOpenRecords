"""
...module:: upload.views.

    :synopsis: Handles Upload endpoints for NYC OpenRecords
"""
import os

from flask import (
    request,
    jsonify,
    current_app,
)
from werkzeug.utils import secure_filename

from app import upload_redis as redis
from . import upload
from .constants import (
    CONTENT_RANGE_HEADER,
    UPLOAD_STATUS
)
from .utils import (
    parse_content_range,
    is_valid_file_type,
    scan_and_complete_upload,
    get_upload_key,
)


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
    key = get_upload_key(request_id, filename)

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
                redis.set(key, UPLOAD_STATUS.PROCESSING)
                with open(filepath, 'ab') as fp:
                    fp.seek(start)
                    fp.write(file_.stream.read())
                # scan if last chunk written
                if os.path.getsize(filepath) == size:
                    scan_and_complete_upload.delay(request_id, filepath)
        else:
            valid_file_type, file_type = is_valid_file_type(file_)
            if valid_file_type:
                redis.set(key, UPLOAD_STATUS.PROCESSING)
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
                }]
            }
    except Exception as e:
        redis.set(key, UPLOAD_STATUS.ERROR)
        print("Upload for file '{}' failed: {}".format(filename, e))
        response = {
            "files": [{
                "name": filename,
                "error": "Error uploading file."
            }]
        }
    return jsonify(response), 200


@upload.route('/<r_id_type>/<r_id>/<filename>', methods=['DELETE'])
def delete(r_id_type, r_id, filename):
    """
    Removes an uploaded file.
    NOTE: This can only deal with request ids for now (OP-798)

    :param r_id_type: "response" or "request"
    :param r_id: the Response or Request identifier
    :param filename: the name of the uploaded file

    :returns:
        On success:
            { "deleted": filename }
        On failure:
            { "error": error message }
    """
    #TODO: check current user permissions
    filename = secure_filename(filename)
    try:
        if r_id_type == "request":
            upload_status = redis.get(
                get_upload_key(r_id, filename)).decode("utf-8")
            path_for_status = {
                UPLOAD_STATUS.PROCESSING: current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
                UPLOAD_STATUS.SCANNING: current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
                UPLOAD_STATUS.READY: current_app.config['UPLOAD_DIRECTORY']
            }
            if upload_status is not None:
                filepath = os.path.join(
                    os.path.join(path_for_status[upload_status], r_id),
                    filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    response = {"deleted": filename}
                else:
                    response = {"error": "File not found."}
            else:
                response = {"error": "Upload not found."}
        elif r_id_type == "response":
            # TODO: OP-814
            response = {"error": "Response IDs not yet handled."}
        else:
            response = {"error": "Invalid ID type."}
    except Exception as e:
        print("Error on DELETE /upload/: {}".format(e))
        response = {"error": "Failed to delete '{}'".format(filename)}

    return jsonify(response), 200


@upload.route('/<request_id>', methods=['GET'])
def get(request_id):
    return jsonify({}), 200


@upload.route('/status', methods=['GET'])
def status():
    """
    Check the status of an upload.

    Request Parameters:
        - request_id
        - filename

    :returns: {
        "status": upload status
    }
    """
    try:
        upload_status = redis.get(
            get_upload_key(
                request.args['request_id'],
                secure_filename(request.args['filename'])
            )
        )
        if upload_status is not None:
            response = {"status": upload_status.decode("utf-8")}
        else:
            response = {"error": "Upload status not found."}
        status_code = 200
    except KeyError:
        response = {}
        status_code = 422

    return jsonify(response), status_code
