"""
    auth.errors: Error Handling for the Authentication Blueprint
"""
from flask import redirect, url_for, render_template

from .. import app


@app.errorhandler(400)
def bad_request(e):
    app.logger.error("400 Bad Request\n{}".format(e))
    return render_template("400.html"), 400


@app.errorhandler(401)
def unauthorized(e):
    app.logger.error("401 Unauthorized\n{}".format(e))
    return render_template("401.html"), 401


@app.errorhandler(403)
def access_denied(e):
    app.logger.error("403 Access Denied\n{}".format(e))
    return redirect(url_for('login'))


@app.errorhandler(404)
def page_not_found(e):
    app.logger.error("404 Not Found\n{}".format(e))
    return render_template("404.html"), 404


@app.errorhandler(405)
def method_not_allowed(e):
    app.logger.error("405 Method Not Allowed\n{}".format(e))
    return render_template("405.html"), 405


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error("500 Internal Server Error\n{}".format(e))
    return render_template("500.html"), 500


@app.errorhandler(501)
def unexplained_error(e):
    app.logger.error("501 Unexplained Error\n{}".format(e))
    return render_template("501.html"), 501


@app.errorhandler(502)
def bad_gateway(e):
    app.logger.error("502 Bad Gateway\n{}".format(e))
    render_template("502.html"), 502


@app.errorhandler(503)
def service_unavailable(e):
    app.logger.error("503 Service Unavailable\n{}".format(e))
    render_template("500.html"), 503
