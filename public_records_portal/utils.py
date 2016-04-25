# -*- coding: utf-8 -*-

"""
....public_records_portal.utils

....Implements commonly used functions for handling data
"""
import bleach

def strip_html(html_str):
    """
    a wrapper for bleach.clean() that strips ALL tags from the input
    :param html_str: string that needs to be stripped
    :return: a bleached string
    """
    tags = []
    attr = {}
    styles = []
    strip = True

    return bleach.clean(html_str,
                        tags=tags,
                        attributes=attr,
                        styles=styles,
                        strip=strip)
