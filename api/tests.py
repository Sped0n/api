from django.test import TestCase

# Create your tests here.
from django.test import Client


class ApiTestCase(TestCase):

    def setUp(self):
        c = Client()
        self.resp = c.get('/arc_metric/', format='json')

    def test_status_code(self):
        self.assertIs(self.resp.status_code, 200)

    def test_content_type(self):
        self.assertEqual(self.resp['content-type'], 'application/json')

    def test_return_json(self):
        self.assertJSONEqual(self.resp.content.decode('utf-8'),
                             {"bounce_rate": 0.0, "pageviews": 1, "visit_duration": 0.0, "visitors": 1})
