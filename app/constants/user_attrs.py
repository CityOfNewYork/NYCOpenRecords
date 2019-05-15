class UserEditableFieldsDict(dict):
    """

    """
    _input_keys = [
        'email',
        'phone_number',
        'fax_number',
        'title',
        'organization',
        'address_one',
        'address_two',
        'city',
        'state',
        'zip'
    ]
    _keys = [
        'email',
        'phone_number',
        'fax_number',
        'title',
        'organization',
        'address'
    ]

    def __init__(self,
                 **kwargs):
        super(UserEditableFieldsDict, self).__init__(self)
        self['email'] = kwargs.get('email')
        self['phone_number'] = kwargs.get('phone_number')
        self['fax_number'] = kwargs.get('fax_number')
        self['title'] = kwargs.get('title')
        self['organization'] = kwargs.get('organization')
        self['address'] = UserAddressDict(
            address_one=kwargs.get('address_one'),
            address_two=kwargs.get('address_two'),
            city=kwargs.get('city'),
            state=kwargs.get('state'),
            zip=kwargs.get('zip')
        )

    def __setitem__(self, key, value):
        if key not in UserEditableFieldsDict._keys:
            raise KeyError
        if key == 'address':
            if not isinstance(value, UserAddressDict):
                raise TypeError
        dict.__setitem__(self, key, value)

    @property
    def is_valid(self):
        for k in self.keys():
            if isinstance(self[k], UserAddressDict):
                if self[k].is_valid:
                    return True
            else:
                if self[k] is not None:
                    return True
        return False


class UserAddressDict(dict):
    """

    """
    _keys = [
        'address_one',
        'address_two',
        'city',
        'state',
        'zip'
    ]

    _valid_keys = [
        'address_one',
        'city',
        'state',
        'zip'
    ]

    def __init__(self, **kwargs):
        super(UserAddressDict, self).__init__(self)
        self['address_one'] = kwargs.get('address_one')
        self['address_two'] = kwargs.get('address_two')
        self['city'] = kwargs.get('city')
        self['state'] = kwargs.get('state')
        self['zip'] = kwargs.get('zip')

    def __setitem__(self, key, value):
        if key not in UserAddressDict._keys:
            raise KeyError
        dict.__setitem__(self, key, value)

    @property
    def is_valid(self):
        for k in UserAddressDict._valid_keys:
            if self[k] is None:
                return False
        return True


class UserStatusDict(dict):
    """

    """
    _keys = [
        'is_agency_admin',
        'is_agency_active',
        'is_super'
    ]

    def __init__(self, **kwargs):
        super(UserStatusDict, self).__init__(self)
        self['is_agency_admin'] = kwargs.get('is_agency_admin')
        self['is_agency_active'] = kwargs.get('is_agency_active')
        self['is_super'] = kwargs.get('is_super')

    def __setitem__(self, key, value):
        if key not in UserStatusDict._keys:
            raise KeyError
        dict.__setitem__(self, key, value)

    @property
    def is_valid(self):
        valid = [val for val in self.values() if val is not None]

        if valid:
            return True
        return False