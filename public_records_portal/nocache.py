from flask import make_response
from functools import wraps, update_wrapper
from datetime import datetime

def nocache(view):
    """
    This function takes in the http response from the browser and disables caching.
    :param view: flask's data of the rendered web page
    :return: modified response with caching disabled
    """
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)
