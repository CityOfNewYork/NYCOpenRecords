import logging
from flask import (request)
from flask_login import current_user
from datetime import datetime


class ContextualFilter(logging.Filter):
    """Contextual Filter for Log Messages"""

    def filter(self, log_record):
        """ Provide some extra variables to give our logs some better info """
        log_record.utcnow = (datetime.utcnow()
                             .strftime('%Y-%m-%d %H:%M:%S,%f %Z'))
        log_record.url = request.path
        log_record.method = request.method
        # Try to get the IP address of the user through reverse proxy
        log_record.ip = request.environ.get('HTTP_X_REAL_IP',
                                            request.remote_addr)
        if current_user.is_anonymous():
            log_record.user_id = 'guest'
        else:
            log_record.user_id = current_user.get_id()

        return True

