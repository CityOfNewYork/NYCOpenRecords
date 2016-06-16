from flask import Flask, render_template, session, redirect, url_for, current_app
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    '''
    Landing page that application directs to upon starting up.
    :return: index.html
    '''
    print("abc")
    return render_template('index.html')

@main.route('/view', methods=['GET', 'POST'])
def view():
    '''
    Landing page that application directs to upon starting up.
    :return: index.html
    '''
    print("def")
    return render_template('index.html')

@main.route('/about', methods=['GET'])
def about():
    '''
    Directs to the about page
    :return:
    '''
    return render_template('About/about.html')
