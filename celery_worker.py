"""
.. module:: celery_worker

   :synopsis: Process that runs celery tasks in the application
"""

import os
from app import celery, create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')  # FIXME: creating app twice?!
app.app_context().push()
