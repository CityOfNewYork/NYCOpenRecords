LATEX_TEMPLATE_CONFIG = {
    'block_start_string': '\BLOCK{',
    'block_end_string': '}',
    'variable_start_string': '\VAR{',
    'variable_end_string': '}',
    'comment_start_string': '\#{',
    'comment_end_string': '}',
    'line_statement_prefix': '%%',
    'line_comment_prefix': '%#',
    'trim_blocks': True,
    'autoescape': False
}


class EnvelopeDict(dict):
    """
    Dict with pre-set keys used for filling in a default envelope template.

    Sample Dictionary:

    {
        'request_id': 'REQUEST ID',
        'recipient_name': 'NAME',
        'organization': 'ORGANIZATION',
        'street_address': 'STREET ADDRESS',
        'city': 'CITY',
        'state': 'STATE',
        'zipcode: 'ZIPCODE'
    }
    """

    _keys = ['request_id', 'recipient_name', 'organization', 'street_address', 'city', 'state', 'zipcode']

    def __init__(self,
                 **kwargs):
        super(EnvelopeDict, self).__init__(self)
        self['request_id'] = kwargs.get('request_id')
        self['recipient_name'] = kwargs.get('recipient_name')
        self['organization'] = kwargs.get('organization')
        self['street_address'] = kwargs.get('street_address')
        self['city'] = kwargs.get('city')
        self['state'] = kwargs.get('state')
        self['zipcode'] = kwargs.get('zipcode')

    def __setitem__(self, key, value):
        if key not in EnvelopeDict._keys:
            raise KeyError
        dict.__setitem__(self, key, value)
