"""Single-owner signed-cookie authentication for a TLS-terminated deployment."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie, CookieError

PASSWORD=os.environ.get('KARNAMA_PASSWORD','')
SECRET=os.environ.get('SESSION_SECRET','') or secrets.token_hex(32)
_lock=threading.Lock()
_attempts=[]

def configured(): return bool(PASSWORD)

def authenticate(password):
    with _lock:
        now=time.time(); _attempts[:]=[t for t in _attempts if now-t<60]
        if len(_attempts)>=10: return None
        _attempts.append(now)
    return hmac.compare_digest(hashlib.sha256(password.encode()).digest(),hashlib.sha256(PASSWORD.encode()).digest())

def issue():
    value=f'{int(time.time())+86400}.{secrets.token_hex(16)}'
    return value+'.'+hmac.new(SECRET.encode(),value.encode(),hashlib.sha256).hexdigest()

def valid(headers):
    if not configured(): return True
    try:
        cookies=SimpleCookie(); cookies.load(headers.get('Cookie',''))
        token=cookies['karnama'].value
        value,signature=token.rsplit('.',1)
        expiry,_=value.split('.',1)
        expected=hmac.new(SECRET.encode(),value.encode(),hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,signature) and time.time()<int(expiry)<=time.time()+86500
    except (KeyError,ValueError,CookieError): return False

LOGIN='''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ورود به کارنما</title><style>body{background:#f2f6f2;color:#244e3d;font:16px Tahoma;max-width:420px;margin:12vh auto;padding:25px}input,button{box-sizing:border-box;width:100%;padding:15px;margin:12px 0;border:1px solid #ccd8ca;border-radius:8px}button{background:#236b52;color:white}p{line-height:2}</style><h1>ورود به کارنما</h1><p>رمز فضای کاری خودتان را وارد کنید؛ نه رمز حساب کارلنسر.</p><form><input type="password" autocomplete="current-password" required placeholder="رمز فضای کاری"><button>ورود امن</button></form><p id="message"></p><script>document.querySelector('form').onsubmit=async e=>{e.preventDefault();try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.querySelector('input').value})});if(r.ok)location.href='/';else document.querySelector('#message').textContent='ورود ناموفق؛ رمز را بررسی کنید یا یک دقیقه صبر کنید.'}catch(e){document.querySelector('#message').textContent='خطای ارتباط با سرور'}}</script></html>'''
