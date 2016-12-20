def has_permission(perm, permission_value):
    """
    Given a permission value, check if the specified permission is activated.
    :param perm: Specific permission (one of app.constants.permission)
    :param permission_value: Permission Value (UserRequests.permissions)
    :return: Boolean
    """
    return bool(permission_value & perm.permissions)
