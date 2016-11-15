from datetime import datetime
from unittest.mock import patch

from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    RequestsFactory,
    create_user,
)
from app.constants.submission_methods import IN_PERSON
from app.constants.request_status import OVERDUE
from app.models import (
    Requests,
    Roles,
    Users,
)
from app.lib.db_utils import (
    create_object,
    update_object,
)


class CreateObjectTests(BaseTestCase):

    def test_object_created(self):
        self.assertFalse(Users.query.first())
        create_user()
        self.assertTrue(Users.query.first())

    def test_es_doc_not_created(self):
        try:
            create_user()  # Users - model without 'es_create' method
        except AttributeError:
            self.fail('es_create() called when it should not have been.')

    @patch('app.models.Requests.es_create')
    def test_request_es_doc_not_created(self, es_create_patch):
        create_object(
            Requests(
                'FOIL-COT',
                title="Where's my money Denny?",
                description="Oh Hi!",
                agency_ein=54,
                date_created=datetime.utcnow(),
                date_submitted=datetime.utcnow(),
                due_date=datetime.utcnow(),
                submission=IN_PERSON,
                status=OVERDUE
            )
        )
        self.assertFalse(es_create_patch.called)


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
