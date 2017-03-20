from tests.lib.base import BaseTestCase
from tests.lib.tools import RequestFactory


class ResponseViewsTests(BaseTestCase):
    # def setUp(self):

    def test_response_closing(self):
        request = RequestFactory().create_request_as_anonymous_user()
        request.acknowledge(days=30)
        self.client.post(
            '/response/closing/' + request.id,
            data={
                "request_id": request.id,
                "email_summary": 'This is a email summary'
            }
        )
