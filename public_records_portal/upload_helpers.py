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

# These are the extensions that can be uploaded:
ALLOWED_EXTENSIONS = ['txt', 'pdf', 'doc', 'rtf', 'odt', 'odp', 'ods',
                      'odg', 'odf', 'ppt', 'pps', 'xls', 'docx', 'pptx',
                      'ppsx', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'tif',
                      'tiff', 'bmp', 'avi', 'flv', 'wmv', 'mov', 'mp4', 'mp3',
                      'wma', 'wav', 'ra', 'mid']
ALLOWED_MIMETYPES = [
'Apple Desktop Services Store',
'RIFF (little-endian) data, AVI',
'PC bitmap',
'Composite Document File V2 Document, Little Endian, Os: MacOS, Version 10.3, Code page: 10000, Author: Joel Castillo, Template: Normal.dotm, Last Saved By: Joel Castillo, Revision Number: 2, Name of Creating Application: Microsoft Macintosh Word, Create Time/Date: Fri Jan 29 14:24:00 2016, Last Saved Time/Date: Fri Jan 29 14:24:00 2016, Number of Pages: 1, Number of Words: 5, Number of Characters: 32, Security: 0',
'Microsoft Word 2007+',
'Macromedia Flash Video',
'GIF image data, version 87a, 1502 x 996',
'JPEG image data',
'JPEG image data',
'ISO Media, Apple QuickTime movie, Apple QuickTime (.MOV/QT)',
'MPEG',
'Audio file with ID3 version 2.3.0, contains: MPEG ADTS, layer III, v1, 128 kbps, 44.1 kHz, JntStereo',
'ISO Media, MP4 Base Media v1 [IS0 14496-12:2003]',
'OpenDocument Formula',
'OpenDocument Drawing',
'OpenDocument Presentation',
'OpenDocument Spreadsheet',
'OpenDocument Text',
'PDF document, version 1.3',
'PNG image data, 1502 x 996, 8-bit/color RGB, non-interlaced',
'Composite Document File V2 Document',
'Microsoft PowerPoint 2007+',
'Microsoft PowerPoint 2007+',
'Rich Text Format data, version 1, unknown character set',
'TIFF image data, big-endian',
'TIFF image data, big-endian',
'TIFF',
'ASCII text, with CR line terminators',
'ASCII text',
'RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, stereo 44100 Hz',
'RIFF',
'Microsoft ASF',
'Composite Document File V2 Document',
'Microsoft Excel 2007',
'Microsoft Excel']
CLEAN = 204
INFECTED_AND_REPAIRABLE = 200
INFECTED_NOT_REPAIRABLE = 201
INFECTED = 403


def should_upload():
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

        if allowed_file(document, request_id, privacy):
            file_scanned = scan_file(document, file_length)
            if file_scanned:
                upload_file_locally(document, secure_filename(document.filename), privacy, request_id=request_id)
                return 1, secure_filename(document.filename), None
            else:
                return None, None, None
        else:
            app.logger.error("File: %s mime type is not allowed." % document.filename)
            return False, '', "File type is not allowed."
    else:
        upload_file_locally(document, secure_filename(document.filename), privacy, request_id=request_id)
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


def upload_file_locally(document, filename, privacy, request_id = None):
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


### @export "allowed_file"
def allowed_file(file, request_id, privacy=1):
    '''Checks the mimetype of the file to see if its allowed'''
    ms = magic.open(magic.NONE)
    ms.load()
    mimetype = ms.buffer(file.read())
    app.logger.info("\n\n" + mimetype)
    file.seek(0)
    # loops through the ALLOWED_MIMETYPES list and checks if the file's mimetype is inside.
    for m in ALLOWED_MIMETYPES:
        if m in mimetype:
            return True
    return False