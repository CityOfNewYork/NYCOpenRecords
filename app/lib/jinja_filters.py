from app.constants import response_type, response_privacy


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
        }[response.type]
    return formatted_type


def format_ultimate_determination_reason(reason):
    reasons = reason.split(",")
    reason_li = "".join("<li>{}</li>".format(r) for r in reasons)
    return "<ul>{}</ul>".format(reason_li)
