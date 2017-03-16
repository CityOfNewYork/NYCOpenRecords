from app.constants import permission


def in_permissions(permissions, value):
    """
    Given a permissions mask, check if the specified permission value is within those permissions.

    :param permissions: permissions set as integer mask
    :param value: permission value to look for

    :type permissions: int
    :type value: int

    :return: is value in permissions?
    """
    return bool(permissions & value)


def get_permissions_as_list(permissions):
    """
    Given a permissions mask, return a list of app.constants.permission.PermissionPair
    """
    return [perm for perm in permission.ALL if in_permissions(permissions, perm.value)]
