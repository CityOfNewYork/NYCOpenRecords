#!/usr/bin/python

import os
from datetime import datetime
from config import Config


MIN_ACCESSED_TIME = 1800  # seconds


def clean():
    for dirpath, dirnames, filenames in os.walk(Config.UPLOAD_SERVING_DIRECTORY):
        if not dirnames:
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if datetime.now().timestamp() - os.stat(filepath).st_atime > MIN_ACCESSED_TIME:
                    os.remove(filepath)


if __name__ == "__main__":
    clean()
