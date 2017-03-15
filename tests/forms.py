from flask_login import login_user, logout_user

from tests.lib.base import BaseTestCase
from tests.lib.tools import create_user

from app.constants import user_type_auth
from app.request.forms import SearchRequestsForm


class SearchRequestsFormTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.agency_user = create_user(user_type_auth.AGENCY_USER)

    def test_constructor(self):
        """
        Test class SearchRequestsForm constructor with anonymous user and logged in agency user.
        """
        # anonymous user
        form = SearchRequestsForm()
        self.assertEqual(form.agency_ein.default, None)

        # agency user
        login_user(self.agency_user)
        form = SearchRequestsForm()
        self.assertEqual(form.agency_ein.default, self.agency_user.agency_ein)
        logout_user()
