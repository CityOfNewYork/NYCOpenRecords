from unittest.mock import patch

from tests.base import BaseTestCase
from tests.tools import RequestsFactory

from app.models import Requests, Roles
from app.lib.db_utils import update_object



class UpdateObjectTests(BaseTestCase):

    def setUp(self):
        super(UpdateObjectTests, self).setUp()
        self.request_id = 'FOIL-UOT'
        self.rf = RequestsFactory(self.request_id)

    def refetch_request(self):
        return Requests.query.filter_by(id=self.request_id).first()

    def test_multifield_update(self):
        new_title = "this title is betta, is fasta, is stronga"
        new_description = "it's the batman"
        with patch('app.models.Requests.es_update'):
            update_object({'title': new_title,
                           'description': new_description},
                          Requests,
                          self.request_id)
        req = self.refetch_request()
        self.assertEqual([req.title, req.description],
                         [new_title, new_description])

    def test_json_update(self):
        self.assertEqual(self.rf.request.privacy,
                         {
                             'title': False,
                             'agency_description': True
                         })
        # check single value change
        with patch('app.models.Requests.es_update'):
            update_object({'privacy': {'title': True}},
                          Requests,
                          self.request_id)
        req = self.refetch_request()
        self.assertEqual(req.privacy,
                         {
                             'title': True,
                             'agency_description': True
                         })
        # check multiple value changes
        with patch('app.models.Requests.es_update'):
            update_object({'privacy': {'title': False,
                                       'agency_description': False}},
                          Requests,
                          self.request_id)
        req = self.refetch_request()
        self.assertEqual(req.privacy,
                         {
                             'title': False,
                             'agency_description': False
                         })

    @patch('app.models.Requests.es_update')
    def test_es_update(self, es_update_patch):
        role = Roles.query.first()
        # check called for model with 'es_update' (Requests)
        update_object({'title': 'new and improved TITLE X50 DELUXE'},
                      Requests,
                      self.request_id)
        es_update_patch.assert_called_once_with()
        # check not called for model without 'es_update' (Roles)
        try:
            update_object({'name': 'nombre'},
                          Roles,
                          role.id)
        except AttributeError:
            self.fail('es_update() called when it should not have been.')
