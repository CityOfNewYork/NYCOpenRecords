from app.constants import (
    response_type,
    response_privacy,
    event_type,
)


def format_response_privacy(privacy):
    return {
        response_privacy.RELEASE_AND_PUBLIC: "Release and Public",
        response_privacy.RELEASE_AND_PRIVATE: "Release and Private",
        response_privacy.PRIVATE: "Private"
    }[privacy]


def format_response_type(response):
    if response.type == response_type.DETERMINATION:
        formatted_type = response.dtype.upper()
    else:
        formatted_type = {
            response_type.NOTE: 'NOTE',
            response_type.EMAIL: 'EMAIL',
            response_type.FILE: 'FILE',
            response_type.INSTRUCTIONS: 'OFFLINE INSTRUCTIONS',
            response_type.LINK: 'LINK',
            response_type.PUSH: 'PUSH NOTIFICATION',
            response_type.SMS: 'SMS',
            response_type.ENVELOPE: 'ENVELOPE',
            response_type.LETTER: 'LETTER'
        }[response.type]
    return formatted_type


def format_ultimate_determination_reason(reason):
    reasons = reason.split("|")
    reason_li = "".join("<li>{}</li>".format(r) for r in reasons)
    return "<ul>{}</ul>".format(reason_li)


def format_event_type(type_):
    return {
        event_type.USER_ADDED: "User Added",
        event_type.USER_REMOVED: "User Removed",
        event_type.USER_PERM_CHANGED: "User Permissions Changed",
        event_type.REQUESTER_INFO_EDITED: "Requester Information Changed",
        event_type.REQ_CREATED: "Request Created",
        event_type.AGENCY_REQ_CREATED: "Request Created by Agency",
        event_type.REQ_ACKNOWLEDGED: "Request Acknowledged",
        event_type.REQ_STATUS_CHANGED: "Request Status Changed",
        event_type.REQ_EXTENDED: "Request Extended",
        event_type.REQ_CLOSED: "Request Closed",
        event_type.REQ_DENIED: "Request Denied",
        event_type.REQ_REOPENED: "Request Re-Opened",
        event_type.REQ_TITLE_EDITED: "Title Changed",
        event_type.REQ_TITLE_PRIVACY_EDITED: "Title Privacy Changed",
        event_type.REQ_AGENCY_REQ_SUM_EDITED: "Agency Request Summary Changed",
        event_type.REQ_AGENCY_REQ_SUM_PRIVACY_EDITED: "Agency Request Summary Privacy Changed",
        event_type.FILE_ADDED: "File Response Added",
        event_type.FILE_EDITED: "File Response Changed",
        event_type.FILE_REMOVED: "File Response Deleted",
        event_type.LINK_ADDED: "Link Response Added",
        event_type.LINK_EDITED: "Link Response Changed",
        event_type.LINK_REMOVED: "Link Response Deleted",
        event_type.INSTRUCTIONS_ADDED: "Offline Instructions Response Added",
        event_type.INSTRUCTIONS_EDITED: "Offline Instructions Response Changed",
        event_type.INSTRUCTIONS_REMOVED: "Offline Instructions Response Deleted",
        event_type.NOTE_ADDED: "Note Response Added",
        event_type.NOTE_EDITED: "Note Response Changed",
        event_type.NOTE_REMOVED: "Note Response Deleted",
    }[type_]
