from django.test import TestCase

# Create your tests here.
from django.test import Client
import os

class ApiTestCase(TestCase):

    def setUp(self):
        c = Client()
        self.resp = c.get('/arc_metric/')

    def test_status_code(self):
        self.assertIs(self.resp.status_code, 200)
        print(self.resp.content)

    def test_content_type(self):
        self.assertEqual(self.resp['content-type'], 'application/json')
