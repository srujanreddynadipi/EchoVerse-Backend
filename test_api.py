import unittest
import json
from app import app

class TestEchoVerseAPI(unittest.TestCase):
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_health_check(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_get_voices(self):
        response = self.app.get('/voices')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('voices', data)
        self.assertTrue(len(data['voices']) > 0)

    def test_get_tones(self):
        response = self.app.get('/tones')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('tones', data)
        self.assertTrue(len(data['tones']) > 0)

    def test_rewrite_endpoint(self):
        payload = {
            'text': 'Hello world',
            'tone': 'cheerful'
        }
        response = self.app.post('/rewrite',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('rewritten_text', data)

    def test_rewrite_invalid_tone(self):
        payload = {
            'text': 'Hello world',
            'tone': 'invalid_tone'
        }
        response = self.app.post('/rewrite',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_rewrite_empty_text(self):
        payload = {
            'text': '',
            'tone': 'neutral'
        }
        response = self.app.post('/rewrite',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
