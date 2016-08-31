from app.main import main

from flask import redirect, url_for


@main.route('/', methods=['GET', 'POST'])
def index():
    return redirect(url_for('auth.login'))
