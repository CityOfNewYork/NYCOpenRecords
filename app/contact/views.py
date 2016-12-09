from flask import(
    render_template,
redirect,
url_for,
request as flask_request,
current_app,
flash,
Markup,
jsonify,
)
@contact.route('/contact', methods=['GET','POST'])
def contact():
    return '<p>Hello</p>'