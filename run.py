from public_records_portal.prflask import app
from os.path import isdir

if isdir('.certs'):
    app.run(host='10.211.55.2',debug=True, port=8080, ssl_context=('.certs/openrecords.crt', '.certs/openrecords.key'))
else:
    app.run(host='10.211.55.2',debug=True, port=8080, ssl_context='adhoc')
