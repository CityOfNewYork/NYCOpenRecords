"""
...module:: upload.views.

    :synopsis: Handles Upload endpoints for NYC OpenRecords
"""
import os
import time
from flask import (
    request,
    jsonify,
    render_template,
    current_app
)
from werkzeug.utils import secure_filename
from . import upload
from .lib import (
    parse_content_range,
    start_file_scan
)
from .constants import CONTENT_RANGE_HEADER

# TODO: include id here and GET, since we are always dealing with a request id in this case?
@upload.route('/', methods=['POST'])
def index():
    """
    Endpoint handles 1 file/chunk at a time.
    """
    # TODO: FE no filesize greater than 500 MB permitted
    files = request.files
    ufile = files[next(files.keys())] # singleFileUploads
    filename = secure_filename(ufile.filename)

    dirr = os.path.join(
        current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
        request.form['request_id'])  # see TODO above def
    if not os.path.exists(dirr):
        os.mkdir(dirr)

    filepath = os.path.join(dirr, filename)

    # try: ...
    if CONTENT_RANGE_HEADER in request.headers:
        start, size = parse_content_range(
            request.headers[CONTENT_RANGE_HEADER])

        with open(filepath, 'ab') as fp:
            fp.seek(start)
            fp.write(ufile.stream.read())

        # TODO: what is commented
        # if os.path.getsize(filepath) == size:
        #     scan_file.delay(filepath)
    else:
        ufile.save(filepath)
        # scan_file.delay(filepath)

    return jsonify({
        "files": [{
            "name": filename,
            "type": 'image/jpeg',
            "size": os.path.getsize(filepath),
            # "url": filepath,
            # "deleteUrl": filepath,
            "deleteType": 'DELETE',
        }]
    }), 200


@upload.route('/test', methods=['GET'])
def test():
    return render_template('upload/uploads.html')


@upload.route('/id/', methods=['GET'])
def uid():
    pass


@upload.route('/status/', methods=['GET'])  # TODO: paused, scanning, ready
def status():
    pass
