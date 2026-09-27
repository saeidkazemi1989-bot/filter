// Network-only: never cache private projects, authenticated HTML or stale monitoring state.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
 if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>new Response('<!doctype html><meta charset="utf-8"><body dir="rtl" style="font:18px Tahoma;padding:40px"><h1>اتصال در دسترس نیست</h1><p>کارنما برای نمایش پروژه‌ها به سرور نیاز دارد. اگر میزبان روشن باشد، پایش روی سرور ادامه دارد.</p><button onclick="location.reload()">تلاش دوباره</button>',{status:503,headers:{'Content-Type':'text/html; charset=utf-8'}})));
});
