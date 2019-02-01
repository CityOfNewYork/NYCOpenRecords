class UserRequestsDict(dict):
    """

    """

    _keys = [
        'user_guid',
        'request_id',
        'request_user_type',
        'permissions',
        'point_of_contact'
    ]

    def __init__(self, **kwargs):
        """

        Args:
            **kwargs:
        """
        super(UserRequestsDict, self).__init__(self)
        self['user_guid'] = kwargs.get('user_guid')
        self['request_id'] = kwargs.get('request_id')
        self['request_user_type'] = kwargs.get('request_user_type')
        self['permissions'] = kwargs.get('permissions')
        self['point_of_contact'] = kwargs.get('point_of_contact')

    def __setitem__(self, key, value):
        if key not in UserRequestsDict._keys:
            raise KeyError
        dict.__setitem__(self, key, value)


class UserRequestsEventDict(dict):
    """

    """

    _keys = [
        'id',
        'request_id',
        'user_guid',
        'response_id',
        'type',
        'timestamp',
        'previous_value',
        'new_value'
    ]

    def __init__(self, **kwargs):
        """

        Args:
            **kwargs:
        """
        super(UserRequestsEventDict, self).__init__(self)
        self['id'] = kwargs.get('id')
        self['request_id'] = kwargs.get('request_id')
        self['user_guid'] = kwargs.get('user_guid')
        self['response_id'] = kwargs.get('response_id')
        self['type'] = kwargs.get('type')
        self['timestamp'] = kwargs.get('timestamp')
        self['previous_value'] = kwargs.get('previous_value')
        self['new_value'] = kwargs.get('new_value')

    def __setitem__(self, key, value):
        if key not in UserRequestsEventDict._keys:
            raise KeyError
        dict.__setitem__(self, key, value)


class EventsDict(dict):
    """

    """
    _keys = [
        'id',
        'request_id',
        'user_guid',
        'response_id',
        'type',
        'timestamp',
        'previous_value',
        'new_value',
    ]

    def __init__(self, **kwargs):
        super(EventsDict, self).__init__(self)
        self['id'] = kwargs.get('id')
        self['request_id'] = kwargs.get('request_id')
        self['user_guid'] = kwargs.get('user_guid')
        self['response_id'] = kwargs.get('response_id')
        self['type'] = kwargs.get('type')
        self['timestamp'] = kwargs.get('timestamp')
        self['previous_value'] = kwargs.get('previous_value')
        self['new_value'] = kwargs.get('new_value')

    def __setitem__(self, key, value):
        if key not in EventsDict._keys:
            raise KeyError
        dict.__setitem__(self, key, value)
