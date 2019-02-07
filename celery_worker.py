"""
.. module:: celery_worker

   :synopsis: Process that runs celery tasks in the application
"""

import os
from app import celery, create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.app_context().push()
