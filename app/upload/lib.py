"""
Helper functions for upload.

"""

import subprocess


def parse_content_range(header):
    """
    """
    bytes = header.split(' ')[1]
    return int(bytes.split('-')[0]), int(bytes.split('/')[1])

# TODO: do not include
def start_file_scan(filepath):
    """

    :param filepath:
    :return:
    """
    subprocess.Popen(['uvscan', filepath])  # TODO: PIPE output to logfile
    # wait and move to /data/directory/
