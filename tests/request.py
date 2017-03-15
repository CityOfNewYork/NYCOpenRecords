from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from flask import jsonify
from unittest.mock import patch

from tests.lib.base import BaseTestCase
from tests.lib.tools import create_user

from app.constants import user_type_auth
from app.lib.date_utils import get_holidays_date_list, DEFAULT_YEARS_HOLIDAY_LIST


class RequestViewsTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.agency_user = create_user(user_type_auth.AGENCY_USER)

    @patch('app.request.views.SearchRequestsForm')
    @patch('app.request.views.render_template', return_value=jsonify({}))  # FIXME: return_value
    def test_view_all_agency(self, render_template_patch, search_requests_form_patch):
        """
        Test render_template in request.views.view_all is called once for logged in agency user.

        :param render_template_patch: patch render_template method from request.views
        :param search_requests_form_patch: patch SearchRequestsForm form object from request.views
        """
        # login agency_user
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = self.agency_user.get_id()
                session['_fresh'] = True
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

        :param render_template_patch: patch render_template method from request.views
        :param search_requests_form_patch: patch SearchRequestsForm form object from request.views
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
