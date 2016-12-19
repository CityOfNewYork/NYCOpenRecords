from app.constants import permission


def has_permission(perm, permission_value):
    """
    Given a permission value, check if the specified permission is activated.
    :param perm: Specific permission
    :param permission_value: Permission Value
    :return: Boolean
    """
    return bool(permission_value & perm.permissions)