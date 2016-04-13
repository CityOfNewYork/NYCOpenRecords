from public_records_portal.prflask import app
from os.path import isdir

if isdir('.certs'):
    app.run(debug=True, port=8080)
else:
    app.run(debug=True, port=8080)
