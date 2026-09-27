"""Conservative public-page monitor: no account, private API, captcha or proxy bypass."""
import json
import os
import re
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, unquote, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.robotparser import RobotFileParser

BASE = 'https://www.karlancer.com'
PAGE = BASE + '/search'
AGENT = 'KarnamaBot/0.2 (+public-project-monitor; interval=30min)'
LIMIT = 4_000_000

class MonitorError(Exception): pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MonitorError('تغییر مسیر دریافت شد؛ ورود یا تغییر آدرس سایت باید بررسی شود.')

def fetch_public(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'www.karlancer.com' or parsed.path not in ('/robots.txt', '/search') or parsed.query:
        raise MonitorError('این مسیر در فهرست مجاز دریافت عمومی نیست.')
    try:
        request = Request(url, headers={'User-Agent':AGENT, 'Accept':'text/html,text/plain', 'Accept-Encoding':'identity'})
        with build_opener(NoRedirect()).open(request, timeout=25) as response:
            raw = response.read(LIMIT + 1)
            if len(raw)>LIMIT: raise MonitorError('اندازه پاسخ بیشتر از حد مجاز است.')
            return raw.decode('utf-8-sig', errors='replace')
    except HTTPError as error:
        if error.code in (401,403,429):
            raise MonitorError(f'سایت دسترسی را محدود کرده است (HTTP {error.code})؛ محدودیت دور زده نمی‌شود.') from None
        raise MonitorError(f'خطای سایت (HTTP {error.code})؛ در نوبت بعد تلاش می‌شود.') from None
    except (URLError, TimeoutError, OSError):
        raise MonitorError('ارتباط HTTPS با کارلنسر برقرار نشد؛ شبکه میزبان و دسترسی به سایت را بررسی کنید.') from None

class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.links=[]; self.anchor=None; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.skip+=1
        if self.skip: return
        if tag=='a':
            href=dict(attrs).get('href','')
            u=urlparse(urljoin(BASE,href))
            if u.scheme=='https' and u.netloc=='www.karlancer.com' and u.path.startswith('/projects/') and len(u.path)>10:
                path=quote(unquote(u.path).rstrip('/'),safe='/')
                self.anchor={'url':BASE+path,'start':len(self.parts),'title':[]}
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'):
            self.skip=max(0,self.skip-1)
        if tag=='a' and self.anchor:
            self.anchor['title']=' '.join(self.anchor['title']).strip()
            self.links.append(self.anchor); self.anchor=None
    def handle_data(self, data):
        if self.skip: return
        text=' '.join(data.split())
        if text:
            self.parts.append(text)
            if self.anchor: self.anchor['title'].append(text)

def parse_listing(html):
    p=ListingParser(); p.feed(html)
    # A title-bearing project link starts a card; repeated generic action links do not.
    generic={'مشاهده پروژه','جزئیات پروژه','ثبت پیشنهاد','مشاهده','مشاهده جزئیات'}
    links=[]; seen=set()
    for link in p.links:
        if len(link['title'])>=3 and link['title'] not in generic and link['url'] not in seen:
            links.append(link); seen.add(link['url'])
    jobs=[]
    for i, link in enumerate(links[:50]):
        end=links[i+1]['start'] if i+1<len(links) else len(p.parts)
        text='\n'.join(p.parts[link['start']:end])
        # Keep only card content, not sharing controls/footer or another source's instructions.
        for boundary in ('مشاهده جزئیات پیشنهادهای این پروژه','گزارش تخلف','پروژه را با دوستان','دسترسی‌ها','مهارت‌های برتر'):
            text=text.split(boundary)[0]
        if len(text)<30: continue
        jobs.append({'title':link['title'][:180],'description':text[:18000], 'source':'کارلنسر · پایش عمومی','url':link['url']})
    if not jobs:
        raise MonitorError('هیچ کارت قابل استخراجی در HTML پیدا نشد؛ احتمال تغییر ساختار، صفحه ورود یا نیاز به جاوااسکریپت. این نتیجه به معنی نبود پروژه نیست.')
    return jobs

def public_jobs(fetch=fetch_public):
    robots=fetch(BASE+'/robots.txt')
    if 'user-agent:' not in robots.lower(): raise MonitorError('robots.txt معتبر دریافت نشد؛ دریافت آگهی متوقف شد.')
    policy=RobotFileParser(); policy.parse(robots.splitlines())
    if not policy.can_fetch(AGENT,PAGE): raise MonitorError('دریافت صفحه پروژه‌ها در robots.txt مجاز نیست؛ پایش متوقف شد.')
    delay=policy.crawl_delay(AGENT) or policy.crawl_delay('*') or 0
    if delay>1800: raise MonitorError('فاصله مجاز درخواست سایت بیشتر از فاصله این پایشگر است؛ تنظیم اتصال نیاز به بررسی دارد.')
    if delay: time.sleep(delay)
    return parse_listing(fetch(PAGE))

def send_email(subject, body):
    required=('SMTP_HOST','SMTP_USER','SMTP_PASSWORD','NOTIFY_EMAIL','PUBLIC_URL')
    if not all(os.environ.get(k) for k in required): return 'not_configured'
    msg=EmailMessage(); msg['Subject']=subject; msg['From']=os.environ['SMTP_USER']; msg['To']=os.environ['NOTIFY_EMAIL']
    msg.set_content(body+'\n\n'+os.environ['PUBLIC_URL'])
    try:
        with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.environ.get('SMTP_PORT','587')),timeout=20) as client:
            client.ehlo(); client.starttls(context=ssl.create_default_context()); client.ehlo()
            client.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']); client.send_message(msg)
        return 'sent'
    except Exception:
        return 'failed'

class Monitor:
    def __init__(self, database, add_job, fetch=fetch_public):
        self.database=database; self.add_job=add_job; self.fetch=fetch
        self.lock=threading.Lock(); self.wake=threading.Event(); self.stop=threading.Event()
        with database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS monitor (id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS imported_urls (url TEXT PRIMARY KEY, job_id INTEGER NOT NULL)')
            state={'enabled':True,'interval':1800,'rate':350000,'last_attempt':0,'last_success':0,'next_run':0,'status':'pending','message':'منتظر اولین بررسی خودکار','added':0,'total':0,'email':'not_configured'}
            db.execute('INSERT OR IGNORE INTO monitor VALUES (1,?)',(json.dumps(state),))
    def state(self):
        with self.database() as db: state=json.loads(db.execute('SELECT state FROM monitor WHERE id=1').fetchone()[0])
        state['running']=self.lock.locked()
        return state
    def update(self, **fields):
        with self.database() as db:
            db.execute('BEGIN IMMEDIATE')
            state=json.loads(db.execute('SELECT state FROM monitor WHERE id=1').fetchone()[0]); state.update(fields)
            state.pop('running',None)
            db.execute('UPDATE monitor SET state=? WHERE id=1',(json.dumps(state),))
    def configure(self, enabled, rate):
        if not isinstance(enabled,bool) or not isinstance(rate,int) or not 10000<=rate<=10000000: raise ValueError('invalid settings')
        self.update(enabled=enabled,rate=rate)
        self.wake.set()
    def request_scan(self):
        state=self.state()
        if state['running'] or time.time()-state['last_attempt']<60: return False
        self.update(next_run=0,enabled=True); self.wake.set(); return True
    def scan(self):
        if not self.lock.acquire(blocking=False): return
        state=self.state(); now=time.time()
        self.update(last_attempt=now,status='running',message='در حال بررسی صفحه عمومی کارلنسر…')
        try:
            items=public_jobs(self.fetch); added=0
            with self.database() as db:
                db.execute('BEGIN IMMEDIATE')
                for item in items:
                    if db.execute('SELECT 1 FROM imported_urls WHERE url=?',(item['url'],)).fetchone(): continue
                    existing=db.execute('SELECT id FROM jobs WHERE url=? AND sample=0',(item['url'],)).fetchone()
                    if existing: job_id=existing[0]
                    else:
                        item['rate']=state['rate']; job_id=self.add_job(db,item); added+=1
                    db.execute('INSERT INTO imported_urls VALUES (?,?)',(item['url'],job_id))
            email=send_email('کارنما: فرصت‌های تازه برای بررسی',f'{added} آگهی جدید پیدا شد. پیش از پیشنهاد، دامنه و قیمت را بازبینی کنید.') if added else state['email']
            self.update(status='ok',last_success=time.time(),added=added,total=state['total']+added,email=email,message=f'{len(items)} کارت عمومی بررسی شد؛ {added} آگهی تازه اضافه شد. فقط صفحه اول بررسی می‌شود.')
        except Exception as error:
            message=str(error) if isinstance(error,MonitorError) else 'خطای داخلی پایش؛ نیازمند بررسی فنی. اطلاعات حساس در گزارش نمایش داده نمی‌شود.'
            email=send_email('کارنما: پایش به بررسی نیاز دارد',message) if state['status']!='error' else state['email']
            self.update(status='error',message=message,added=0,email=email)
        finally:
            self.update(next_run=time.time()+state['interval']); self.lock.release()
    def loop(self):
        while not self.stop.is_set():
            state=self.state()
            if state['enabled'] and time.time()>=state['next_run']: self.scan()
            self.wake.wait(15); self.wake.clear()
    def start(self):
        threading.Thread(target=self.loop,name='public-monitor',daemon=True).start()
