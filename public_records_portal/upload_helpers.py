"""
    public_records_portal.upload_helpers
    ~~~~~~~~~~~~~~~~

    Implements functions to upload files

"""

import os
import socket
import datetime

from werkzeug.utils import secure_filename

from public_records_portal import app
from models import RecordPrivacy


def should_upload():
    if app.config['ENVIRONMENT'] != 'LOCAL':
        return True
    return False


# These are the extensions that can be uploaded:
ALLOWED_EXTENSIONS = ['txt', 'pdf', 'doc', 'rtf', 'odt', 'odp', 'ods', 
                      'odg', 'odf', 'ppt', 'pps', 'xls', 'docx', 'pptx', 
                      'ppsx', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'tif', 
                      'tiff', 'bmp', 'avi', 'flv', 'wmv', 'mov', 'mp4', 'mp3', 
                      'wma', 'wav', 'ra', 'mid']


def upload_multiple_files(documents, request_id):
    """
    Uploads a list of documents one by one.
    :param documents: list of files (documents)
    :param request_id: FOIL Request ID Number
    :return: None
    """
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

        if allowed_file(document.filename):
            file_scanned = scan_file(document, file_length)
            if file_scanned == 0:
                upload_file_locally(document, secure_filename(document.filename), privacy)
                return 1, secure_filename(document.filename), None
            else:
                return None, None, None
        else:
            return None
    else:
        upload_file_locally(document, secure_filename(document.filename), privacy)
        return 1, secure_filename(document.filename), None


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
        sock.connect(app.config['ICAP_SERVER_HOST'], app.config['ICAP_SERVER_PORT'])
    except socket.error, msg:
        app.logger.error("Error connection to ICAP Server\n%s\n" % msg[1])
        return False

    # Create ICAP Request Header
    filename = document.filename
    request_header = "GET http://%s/%s/%s HTTP/1.1\r\nHost: %s\r\n\r\n" % \
                     (app.config['ICAP_CLIENT_HOST'], datetime.datetime.now().strftime("%Y%m%D%H%M%S"), filename,
                      app.config['ICAP_CLIENT_HOST'])

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

    # Convert file to bytearray
    file_to_scan = document.read()
    file_as_bytearray = bytearray(file_to_scan)

    app.logger.info("Length of File: %s" % len(file_as_bytearray))

    # Send file to ICAP Server
    header_seperator = str(hex(file_length)).split('0x')[-1] + "\r\n"
    sock.send(header_seperator)
    total_sent = 0
    while total_sent < file_length:
        sent = sock.send(file_as_bytearray[total_sent:])
        if sent == 0:
            app.logger.info("Socket connection broken\n")
            return False
        total_sent = total_sent + sent

    sock.send("\r\n0\r\n\r\n")

    # Get ICAP Response
    result = sock.recv()

    # Parse ICAP Response
    if result.startswith(app.config['ICAP_VERSION'], 0):
        results = result.split(" ", 3)
        code = int(results[1])
        if INFECTED_AND_REPAIRABLE == code:
            app.logger.info("Infected but Repairable\n")
        else:
            app.logger.info("VIrus Scan Result: %s\n" % results[2])
            if results[2] == CLEAN:



def upload_file_locally(document, filename, privacy):
    app.logger.info("\n\nuploading file locally")
    app.logger.info("\n\n%s" % (document))

    if privacy == RecordPrivacy.RELEASED_AND_PUBLIC:
        upload_path = os.path.join(app.config['UPLOAD_PUBLIC_LOCAL_FOLDER'], filename)
    else:
        upload_path = os.path.join(app.config['UPLOAD_PRIVATE_LOCAL_FOLDER'], filename)
    app.logger.info("\n\nupload path: %s" % (upload_path))

    document.save(upload_path)

    app.logger.info("\n\nfile uploaded to local successfully")

    return upload_path


### @export "allowed_file"
def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1]
    return ext in ALLOWED_EXTENSIONS
