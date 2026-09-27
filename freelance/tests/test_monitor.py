import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('monitor_server',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
from monitor import Monitor, MonitorError, parse_listing, public_jobs, fetch_public
import auth

HTML='''<html><script>private data ignored</script><a href="/projects/first-123"><h2>طراحی سایت فروشگاهی</h2></a><p>بودجه</p><p>۳۰۰۰۰۰۰ تومان</p><p>یک صفحه معرفی محصولات با طراحی واکنش‌گرا و امکانات فارسی نیاز داریم.</p><a href="/projects/first-123">مشاهده پروژه</a><p>مشاهده جزئیات پیشنهادهای این پروژه</p><footer>نباید وارد شرح شود</footer><a href="https://www.karlancer.com/projects/second-456"><strong>اتوماسیون پایتون</strong></a><p>نیازمند تبدیل فایل‌های اکسل و گزارش خروجی با پایتون و تست روی نمونه فایل هستیم.</p><p>گزارش تخلف</p><p>دسترسی‌ها</p></html>'''
ROBOTS='User-agent: *\nDisallow: /api\nDisallow: /panel/\n'

class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();s.DB=Path(self.tmp.name)/'test.db'
    def tearDown(self): self.tmp.cleanup()
    def fake(self,url): return ROBOTS if url.endswith('robots.txt') else HTML
    def test_parse_card_boundaries(self):
        rows=parse_listing(HTML)
        self.assertEqual(len(rows),2)
        self.assertNotIn('نباید',rows[0]['description']);self.assertNotIn('private data',str(rows))
        self.assertNotIn('دسترسی‌ها',rows[1]['description'])
    def test_zero_cards_is_error(self):
        with self.assertRaises(MonitorError):parse_listing('<h1>Login or captcha</h1>')
    def test_disallowed_no_page_fetch(self):
        calls=[]
        def fetch(url):calls.append(url);return 'User-agent: *\nDisallow: /search'
        with self.assertRaises(MonitorError):public_jobs(fetch)
        self.assertEqual(len(calls),1)
    def test_no_private_or_foreign_requests(self):
        for url in ['https://www.karlancer.com/api/jobs','https://www.karlancer.com/panel/','https://evil.test/search','http://www.karlancer.com/search','https://www.karlancer.com/search?q=test']:
            with self.assertRaises(MonitorError):fetch_public(url)
    def test_scan_dedup_restart_keeps_status(self):
        m=Monitor(s.database,s.add_job,self.fake);m.scan();self.assertEqual(m.state()['added'],2)
        with s.database() as db:db.execute("UPDATE jobs SET status='agreed'")
        m=Monitor(s.database,s.add_job,self.fake);m.scan();self.assertEqual(m.state()['added'],0)
        with s.database() as db:
            rows=db.execute('SELECT * FROM jobs').fetchall();self.assertEqual(len(rows),2);self.assertTrue(all(r['status']=='agreed' for r in rows))
    def test_error_retains_success_and_no_fake_data(self):
        m=Monitor(s.database,s.add_job,self.fake);m.scan();success=m.state()['last_success']
        def fail(url):raise MonitorError('network unavailable')
        m.fetch=fail;m.scan();self.assertEqual(m.state()['status'],'error');self.assertEqual(m.state()['last_success'],success)
        self.assertEqual(m.state()['added'],0)
    def test_config_and_rate_limit(self):
        m=Monitor(s.database,s.add_job,self.fake);m.configure(False,500000)
        self.assertFalse(m.state()['enabled']);self.assertEqual(m.state()['rate'],500000)
        m.scan();self.assertFalse(m.request_scan())
        with self.assertRaises(ValueError):m.configure('yes',10)
    def test_cookie_integrity_expiry_and_no_secrets(self):
        with patch.object(auth,'PASSWORD','a long workspace password'):
            self.assertFalse(auth.valid({}))
            token=auth.issue();self.assertTrue(auth.valid({'Cookie':'karnama='+token}))
            self.assertFalse(auth.valid({'Cookie':'karnama='+token+'bad'}))
            with patch('auth.time.time',return_value=9999999999): self.assertFalse(auth.valid({'Cookie':'karnama='+token}))
