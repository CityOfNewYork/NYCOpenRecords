from app.constants import response_privacy


def format_response_privacy(privacy):
    # FIXME: doesn't 'Public Release' make more sense? (if so, change for every occurrence)
    return {
        response_privacy.RELEASE_AND_PUBLIC: "Release and Public",
        response_privacy.RELEASE_AND_PRIVATE: "Release and Private",
        response_privacy.PRIVATE: "Private"
    }[privacy]
