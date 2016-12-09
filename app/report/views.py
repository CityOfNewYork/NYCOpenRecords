from app.report import report
from flask import render_template


@report.route('/view', methods=['GET'])
def index():
    return '<h1> The Reports Page </h1>'