from urllib.parse import urljoin


OAUTH_BASE_ENDPOINT = "account/api/oauth/"
AUTH_ENDPOINT = urljoin(OAUTH_BASE_ENDPOINT, 'authorize.htm')
USER_ENDPOINT = urljoin(OAUTH_BASE_ENDPOINT, 'user.htm')

EMAIL_VALIDATION_ENDPOINT = "/account/validateEmail.htm"
EMAIL_VALIDATION_STATUS_ENDPOINT = "/account/api/isEmailValidated.htm"

TOU_ENDPOINT = "/account/user/termsOfUse.htm"
TOU_STATUS_ENDPOINT = "/account/api/isTermsOfUseCurrent.htm"

ENROLLMENT_ENDPOINT = "/account/api/enrollment.htm"
