"""Constants for single-active-session enforcement."""

# Exempt from enforcement so timeout and forced-logout requests can complete
# the NYC.ID logout round trip instead of being intercepted.
SESSION_ENFORCEMENT_EXEMPT_ENDPOINTS = frozenset((
    'static',
    'auth.logout',
    'auth.saml',
))
