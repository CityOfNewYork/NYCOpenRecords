"""
    public_records_portal.upload_helpers
    ~~~~~~~~~~~~~~~~

    Implements functions to upload files

"""

import datetime
import os
import socket

import magic
from werkzeug.utils import secure_filename

from models import RecordPrivacy
from public_records_portal import app

ALLOWED_MIMETYPES = [
                    'video/x-msvideo',
                    'image/x-ms-bmp',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'video/x-flv',
                    'image/gif',
                    'image/jpeg',
                    'video/quicktime',
                    'audio/mpeg',
                    'video/mp4',
                    'application/vnd.oasis.opendocument.formula',
                    'application/vnd.oasis.opendocument.graphics',
                    'application/vnd.oasis.opendocument.presentation',
                    'application/vnd.oasis.opendocument.spreadsheet',
                    'application/vnd.oasis.opendocument.text',
                    'application/pdf',
                    'image/png',
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'text/plain',
                    'text/rtf',
                    'image/tiff',
                    'audio/x-wav',
                    'video/x-ms-asf',
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ]
CLEAN = 204
INFECTED_AND_REPAIRABLE = 200
INFECTED_NOT_REPAIRABLE = 201
INFECTED = 403


def should_upload():
    app.logger.info("def should_upload")
    if app.config['ENVIRONMENT'] != 'LOCAL' or app.config['UPLOAD_DOCS'] == 'True':
        return True
    return False


def upload_multiple_files(documents, request_id):
    """
    Uploads a list of documents one by one.
    :param documents: list of files (documents)
    :param request_id: FOIL Request ID Number
    :return: None
    """
    app.logger.info("def upload_multiple_files")
    for document in documents:
        upload_file(document=document, request_id=request_id)


def upload_file(document, request_id, privacy=0x1):
    """
    Takes an uploaded file, scans it using an ICAP Scanner, and stores the
    file if the scan passed
    :param document: File to be uploaded
    :param request_id: FOIL Request ID Number
    :param privacy: Privacy value for the uploaded document
    :return: (Boolean, String, String)
    """
    app.logger.info("def upload_file")
    if not should_upload():
        # Should the file be uploaded
        app.logger.info("Upload functionality has been disabled\n\n")
        return '1', None, None

    if app.config['SHOULD_SCAN_FILES'] == 'True':
        # Get document size in bytes
        file_length = len(document.read())
        document.seek(0)

        app.logger.info("File Size: %s\nMAX_FILE_SIZE: %s\n" % (file_length, app.config['MAX_FILE_SIZE']))

        # Ensure we can upload the file
        if file_length < 0:
            app.logger.error("File: %s is too small" % document.filename)
            return False, '', "file_too_small"

        if file_length > int(app.config['MAX_FILE_SIZE']):
            app.logger.error("File: %s is too large" % document.filename)
            return False, '', "file_too_large"



        if allowed_file(document):
            file_scanned = scan_file(document, file_length)
            if file_scanned:
                if file_length > int(app.config['MAX_EMAIL_ATTACHMENT_SIZE']):
                    return 1, secure_filename(document.filename), "cannot_email_file"
                upload_file_locally(document, secure_filename(document.filename), privacy, request_id=request_id)
                return 1, secure_filename(document.filename), None
            else:
                return None, None, None
        else:
            app.logger.error("File: %s mime type is not allowed." % document.filename)
            return False, '', "File type is not allowed."
    else:
        if allowed_file(document):
            file_length = len(document.read())
            document.seek(0)
            upload_file_locally(document, secure_filename(document.filename), privacy, request_id=request_id)
            if file_length > int(app.config['MAX_EMAIL_ATTACHMENT_SIZE']):
                return 1, secure_filename(document.filename), "cannot_email_file"
            return 1, secure_filename(document.filename), None
        else:
            app.logger.error("File: %s mime type is not allowed." % document.filename)
            return False, '', "File type is not allowed."


def scan_file(document, file_length):
    """
    Sends a document to an ICAP server for virus scanning.
    :param document: Document that needs to be scanned
    :param file_length: Size of document to be scanned
    :return: Boolean
    """
    app.logger.info("Scanning File: %s" % secure_filename(document.filename))

    # Create Socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error, msg:
        app.logger.error("Error binding socket\n%s\n" % msg[1])
        return False

    # Connect to ICAP Server
    try:
        sock.connect((app.config['ICAP_SERVER_HOST'], int(app.config['ICAP_SERVER_PORT'])))
    except socket.error, msg:
        app.logger.error("Error connection to ICAP Server\n%s\n" % msg[1])
        return False

    # Create ICAP Request Header
    filename = document.filename
    request_header = "GET http://%s/%s/%s HTTP/1.1\r\nHost: %s\r\n\r\n" % \
                     (app.config['ICAP_CLIENT_HOST'], datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                      secure_filename(filename), app.config['ICAP_CLIENT_HOST'])

    # Create ICAP Response Header
    response_header = "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"

    # Create Header Sizes
    request_header_size = 0
    response_header_size = len(request_header)
    response_body = response_header_size + len(response_header)

    # Create ICAP Request Header
    icap_request = "RESPMOD icap://%s:%s/%s%s ICAP/1.0\r\n" \
                   "Allow: 204\r\n" \
                   "Encapsulated: req-hdr=%s res-hdr=%s res-body=%s\r\n" \
                   "Host: %s\r\n" \
                   "User-Agent: PythonICAPClient\r\n" \
                   "X-Client-IP: %s\r\n\r\n" % (app.config['ICAP_SERVER_HOST'], app.config['ICAP_SERVER_PORT'],
                                                app.config['ICAP_SERVICE_NAME'], app.config['ICAP_PROFILE_NAME'],
                                                request_header_size, response_header_size, response_body,
                                                app.config['ICAP_SERVER_HOST'], app.config['ICAP_CLIENT_HOST'])

    app.logger.info("ICAP Request: %s\n" % icap_request)
    app.logger.info("Request Header: %s\n" % request_header)
    app.logger.info("Response Header: %s\n" % response_header)

    sock.send(icap_request)
    sock.send(request_header)
    sock.send(response_header)

    # Convert file to bytearray
    file_to_scan = document.read()
    document.seek(0)
    file_as_bytearray = bytearray(file_to_scan)

    app.logger.info("Length of File: %s" % len(file_as_bytearray))

    # Send file to ICAP Server
    header_separator = str(hex(file_length)).split('0x')[-1] + "\r\n"
    app.logger.info("Header Separator: %s" % header_separator)
    sock.send(header_separator)
    total_sent = 0
    while total_sent < file_length:
        sent = sock.send(file_as_bytearray[total_sent:])
        if sent == 0:
            app.logger.info("Socket connection broken\n")
            return False
        total_sent = total_sent + sent
        app.logger.info("Size: %s\nTotal Sent: %s\n" % (file_length, total_sent))

    sock.send("\r\n0\r\n\r\n")

    # Get ICAP Response
    result = sock.recv(1024)
    app.logger.info("ICAP Result: %s" % result)
    # Parse ICAP Response
    if result.startswith(app.config['ICAP_VERSION'], 0):
        results = result.split(" ", 3)
        code = int(results[1])
        if code == CLEAN:
            return True
        else:
            if code == INFECTED_AND_REPAIRABLE:
                app.logger.info("File: %s is infected but repairable")
                return False
            if code == INFECTED_NOT_REPAIRABLE:
                app.logger.info("File: %s is infected and cannot be fixed")
                return False
            if code == INFECTED:
                app.logger.info("File: %s is infected")
                return False
            if str(code).startswith("4"):
                app.logger.info("ICAP Client Error")
                return False
            if str(code).startswith("5"):
                app.logger.info("ICAP Server Error")
                return False
    return False


def upload_file_locally(document, filename, privacy, request_id=None):
    app.logger.info("\n\nuploading file locally")
    app.logger.info("\n\n%s" % (document))

    if privacy == RecordPrivacy.RELEASED_AND_PUBLIC:
        upload_directory = os.path.join(app.config['UPLOAD_PUBLIC_LOCAL_FOLDER'], request_id)
        upload_path = os.path.join(upload_directory, filename)
        if not os.path.exists(upload_directory):
            os.makedirs(upload_directory)
    else:
        upload_directory = os.path.join(app.config['UPLOAD_PRIVATE_LOCAL_FOLDER'], request_id)
        upload_path = os.path.join(upload_directory, filename)
        if not os.path.exists(upload_directory):
            os.makedirs(upload_directory)

    app.logger.info("\n\nupload path: %s" % (upload_path))

    document.save(upload_path)

    app.logger.info("\n\nfile uploaded to local successfully")

    return upload_path


def allowed_file(file):
    """
    Checks if a file is allowed to be submitted into the database.
    :param file: pass in a file that will be checked for allowed mimetype
    :return: True if the mimetype is allowed or False if its not allowed
    """
    if app.config['MAGIC_FILE'] != '':
        f = magic.Magic(magic_file=app.config['MAGIC_FILE'], mime=True)
    else:
        f = magic.Magic(mime=True)
    mimetype = f.from_buffer(file.read())
    file.seek(0)
    app.logger.info("\n\nMimetype: " + mimetype)
    for m in ALLOWED_MIMETYPES:
        if m in mimetype:
            return True
