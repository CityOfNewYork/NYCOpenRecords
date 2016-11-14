from app.constants import response_type, response_privacy


def format_response_privacy(privacy):
    return {
        response_privacy.RELEASE_AND_PUBLIC: "Release and Public",
        response_privacy.RELEASE_AND_PRIVATE: "Release and Private",
        response_privacy.PRIVATE: "Private"
    }[privacy]


def format_response_type(type_):
    return {
        response_type.NOTE: 'NOTE',
        response_type.EMAIL: 'EMAIL',
        response_type.FILE: 'FILE',
        response_type.INSTRUCTIONS: 'OFFLINE INSTRUCTIONS',
        response_type.EXTENSION: 'EXTENSION',
        response_type.LINK: 'LINK',
        response_type.PUSH: 'PUSH NOTIFICATION',
        response_type.SMS: 'SMS',
    }[type_]
