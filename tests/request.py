from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from flask import jsonify
from unittest.mock import patch

from tests.lib.base import BaseTestCase
from tests.lib.tools import UserFactory, login_user_with_client

from app.lib.date_utils import get_holidays_date_list, DEFAULT_YEARS_HOLIDAY_LIST


class RequestViewsTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        uf = UserFactory()
        self.agency_admin = uf.create_agency_admin()

    @patch('app.request.views.SearchRequestsForm')
    @patch('app.request.views.render_template', return_value=jsonify({}))  # FIXME: return_value
    def test_view_all_agency(self, render_template_patch, search_requests_form_patch):
        """
        Test render_template in request.views.view_all is called once for logged in agency user.
        """
        # login agency_user
        with self.client as client:
            login_user_with_client(client, self.agency_admin.get_id())
            self.client.get('/request/view_all')
            render_template_patch.assert_called_once_with(
                'request/all.html',
                form=search_requests_form_patch(),
                holidays=sorted(get_holidays_date_list(
                    datetime.utcnow().year,
                    (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
                )
            )

    @patch('app.request.views.SearchRequestsForm')
    @patch('app.request.views.render_template', return_value=jsonify({}))
    def test_view_all_anon(self, render_template_patch, search_requests_form_patch):
        """
        Test render_template in request.views.view_all is called once for anonymous user.
        """
        with self.client:
            self.client.get('/request/view_all')
            render_template_patch.assert_called_once_with(
                'request/all.html',
                form=search_requests_form_patch(),
                holidays=sorted(get_holidays_date_list(
                    datetime.utcnow().year,
                    (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
                )
            )
