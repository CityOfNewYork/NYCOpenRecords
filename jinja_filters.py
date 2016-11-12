from app.constants import response_privacy


def privacy_format(privacy):
    if privacy == response_privacy.RELEASE_AND_PUBLIC:
        privacy = "Release and Public"
    elif privacy == response_privacy.RELEASE_AND_PRIVATE:
        privacy = "Release and Private"
    else:
        privacy = "Private"
    return privacy
