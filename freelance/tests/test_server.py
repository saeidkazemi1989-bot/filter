import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location('server', Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s.DB = Path(self.tmp.name) / 'test.db'
        self.server = s.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
    def request(self, path, data=None, origin=None):
        headers = {'Content-Type':'application/json'}
        if origin: headers['Origin'] = origin
        req = urllib.request.Request(self.base+path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req) as response: return response.status, response.read()
        except urllib.error.HTTPError as error: return error.code, error.read()
    def job(self):
        code, body = self.request('/api/jobs', {'title':'طراحی سایت', 'description':'یک سایت فارسی با طراحی واکنش‌گرا برای معرفی محصولات نیاز داریم.'})
        self.assertEqual(code, 201)
        return json.loads(body)['ids'][0]
    def test_hosted_auth_gates_data_and_issues_secure_cookie(self):
        with patch.object(s.auth, 'PASSWORD', 'a-long-test-password'), patch.object(s.auth, 'SECRET', 'test-secret-only'):
            self.assertEqual(self.request('/api/jobs')[0],401)
            self.assertIn('ورود به کارنما', self.request('/')[1].decode())
            self.assertEqual(self.request('/api/login',{'password':'wrong'})[0],401)
            req=urllib.request.Request(self.base+'/api/login',data=json.dumps({'password':'a-long-test-password'}).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req) as response:
                cookie=response.headers['Set-Cookie']
                self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie);self.assertIn('SameSite=Strict',cookie)
            req=urllib.request.Request(self.base+'/api/jobs',headers={'Cookie':cookie.split(';')[0]})
            with urllib.request.urlopen(req) as response:self.assertEqual(response.status,200)

    def test_initial_empty_and_import(self):
        self.assertEqual(json.loads(self.request('/api/jobs')[1]), [])
        self.job()
        job = json.loads(self.request('/api/jobs')[1])[0]
        self.assertEqual(job['sample'], 0)
        self.assertEqual(job['price'], 7000000)
        self.assertEqual(job['status'], 'review')
    def test_samples_idempotent(self):
        for _ in range(2): self.request('/api/samples', {})
        rows = json.loads(self.request('/api/jobs')[1])
        self.assertEqual(len(rows),3)
        self.assertTrue(all(j['sample'] for j in rows))
    def test_transitions_require_evidence(self):
        job_id = self.job(); path=f'/api/jobs/{job_id}'
        self.assertEqual(self.request(path, {'status':'delivered'})[0],400)
        self.assertEqual(self.request(path, {'status':'proposal'})[0],200)
        self.assertEqual(self.request(path, {'status':'agreed'})[0],400)
        self.assertEqual(self.request(path, {'status':'agreed','note':'توافق آزمایشی با دامنه مشخص'})[0],200)
        self.assertEqual(self.request(path, {'status':'execution'})[0],200)
        self.assertEqual(self.request(path, {'status':'review_output','note':'فایل خروجی واقعی بررسی شده است'})[0],200)
        self.assertEqual(self.request(path, {'status':'delivered','note':'خروجی بازبینی و توسط کاربر ارسال شد'})[0],200)
    def test_exports(self):
        job_id = self.job()
        for action in ['demo','brief','package']:
            code, body = self.request(f'/api/jobs/{job_id}/{action}')
            self.assertEqual(code,200); self.assertTrue(body)
        self.assertTrue(self.request(f'/api/jobs/{job_id}/package')[1].startswith(b'PK'))
    def test_escape_and_url_validation(self):
        data={'title':'<script>alert(1)</script>', 'description':'شرح آزمایشی برای بررسی جلوگیری از تزریق اسکریپت', 'url':'javascript:alert(1)'}
        self.assertEqual(self.request('/api/jobs',data)[0],400)
        data['url']='https://example.com'
        job_id=json.loads(self.request('/api/jobs',data)[1])['ids'][0]
        html=self.request(f'/api/jobs/{job_id}/demo')[1].decode()
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
    def test_cross_origin_blocked(self):
        self.assertEqual(self.request('/api/samples',{},'https://evil.example')[0],403)
    def test_batch_atomic(self):
        good={'title':'یک آگهی تست','description':'یک توضیح کافی برای ورود به برنامه'}
        self.assertEqual(self.request('/api/jobs',[good,{}])[0],400)
        self.assertEqual(json.loads(self.request('/api/jobs')[1]),[])
    def test_human_task_low_score(self):
        self.assertLess(s.analyze('طراحی سایت حضوری','پروژه با حضور فیزیکی',350000)[2],70)

if __name__ == '__main__': unittest.main()
