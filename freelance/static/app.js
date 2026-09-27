const $ = s => document.querySelector(s);
const fa = n => Number(n).toLocaleString('fa-IR');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statuses = {review:'نیازمند بازبینی',proposal:'پیشنهاد آماده؛ ارسال دستی',agreed:'توافق ثبت‌شده',execution:'منتظر اجرا در Arena',review_output:'بازبینی خروجی',delivered:'تحویل ثبت‌شده توسط شما',archived:'بایگانی'};
let jobs = [], filter = 'all', view = 'opportunities', selected = null;
let rate = Number(localStorage.getItem('karnama-rate')) || 350000;
$('#rate').value = rate;
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(response.status===401){location.reload();throw new Error('ورود دوباره لازم است.')}
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'عملیات ناموفق بود.');
  return result;
}
let toastTimer;
function toast(text) { $('#toast').textContent=text; $('#toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').hidden=true,6500); }
function alertUser(text) {
  toast(text);
  if ('Notification' in window && Notification.permission==='granted') {
    try { new Notification('کارنما؛ نوبت شماست', {body:text}); } catch (_) { /* In-page alert remains available. */ }
  }
}
async function reload() { jobs=await api('/api/jobs'); render(); }
function card(job) {
  return `<article class="job-card"><div><div class="meta"><span class="source-tag">${esc(job.source)}</span>${job.sample?'<span class="sample-tag">نمونه ساختگی</span>':((job.source.includes('پایش عمومی')||job.source.includes('بررسی اولیه'))?'<span>دریافت از صفحه عمومی</span>':'<span>واردشده توسط شما</span>')}<span>· ${new Date(job.created).toLocaleDateString('fa-IR')}</span></div><h3>${esc(job.title)}</h3><p>${esc(job.description)}</p><div class="chips"><span class="chip">${esc(job.category)}</span><span class="chip">حدود ${fa(job.hours)} ساعت</span><span class="chip">${statuses[job.status]}</span></div></div><div class="job-side"><div class="score ${job.score<70?'low':''}"><span>تناسب اولیه با Arena</span><b>${fa(job.score)} / ۱۰۰</b></div><span class="price-label">پیشنهاد اولیه، قابل مذاکره</span><div class="price">${fa(job.price)} <small>تومان</small></div><button class="detail-button" data-detail="${job.id}">بررسی فرصت و دمو ←</button></div></article>`;
}
function empty(title, text, samples=false) {
 return `<div class="empty"><div class="symbol">◈</div><h3>${title}</h3><p>${text}</p>${samples?'<button class="primary" data-add>اولین آگهی را وارد کنید</button><button class="secondary" data-samples>امتحان با ۳ آگهی نمونه</button>':''}</div>`;
}
function render() {
 const active = jobs.filter(j=>j.status!=='archived' && j.status!=='delivered');
 const matched = active.filter(j=>j.score>=70);
 const wait = jobs.filter(j=>['review','proposal','execution','review_output'].includes(j.status));
 $('#stat-all').textContent=fa(jobs.length);
 $('#stat-match').textContent=fa(matched.length);
 $('#stat-wait').textContent=fa(wait.length);
 $('#attention-count').textContent=fa(wait.length);
 $('#stat-value').innerHTML=`${fa(matched.reduce((n,j)=>n+j.price,0))} <em>تومان</em>`;
 const query=$('#search').value.trim().toLowerCase();
 let list=jobs.filter(j=>(filter!=='matched'||j.score>=70)&&(filter!=='real'||!j.sample)&&`${j.title} ${j.description}`.toLowerCase().includes(query));
 const sort=$('#sort').value;
 if(sort==='score')list.sort((a,b)=>b.score-a.score);
 if(sort==='price')list.sort((a,b)=>b.price-a.price);
 $('#result-count').textContent=`${fa(list.length)} فرصت · امتیازها تخمین قاعده‌محورند`;
 $('#jobs').innerHTML=list.length?list.map(card).join(''):empty(jobs.length?'فرصتی با این فیلتر پیدا نشد':'میز کارتان آماده است.','با واردکردن متن یک آگهی واقعی شروع کنید. برای آشنایی با مراحل می‌توانید داده‌های نمایشی را بارگذاری کنید.',!jobs.length);
 const pipeline=jobs.filter(j=>!['review','archived'].includes(j.status));
 $('#pipeline').innerHTML=pipeline.length?pipeline.map(card).join(''):empty('هنوز پروژه‌ای وارد مسیر اجرا نشده','یک فرصت را باز کنید و پس از بازبینی، پیشنهاد اولیه آن را آماده کنید.');
 $('#attention').innerHTML=wait.length?wait.map(card).join(''):empty('فعلاً کاری منتظر شما نیست','با ورود آگهی، درخواست‌های بازبینی و اقدام شما اینجا نمایش داده می‌شوند.');
}
function openAdd() { $('#add-dialog').showModal(); }
$('#add').onclick=openAdd;
$('#job-form').onsubmit=async e=>{
 e.preventDefault();const button=e.submitter;button.disabled=true;
 try { const data=Object.fromEntries(new FormData(e.target));data.rate=rate;await api('/api/jobs',data);await reload();$('#add-dialog').close();e.target.reset();alertUser('آگهی تحلیل شد. پیش از پیشنهاد، شرح و برآورد را بازبینی کنید.'); }
 catch(error){toast(error.message)} finally {button.disabled=false}
};
const views={opportunities:['فرصت‌های کاری','فرصت بعدی‌تان را پیدا کنید.'],pipeline:['میز پروژه‌ها','از پیشنهاد تا تحویل، مرحله‌به‌مرحله.'],attention:['نیاز به شما','تصمیم‌های مهم، با شما.'],sources:['منابع آگهی','فرصت‌ها از اینجا شروع می‌شوند.'],settings:['تنظیمات برآورد','برآورد را با کار خودتان تنظیم کنید.']};
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{
 view=button.dataset.view;
 document.querySelectorAll('[id^="view-"]').forEach(el=>el.hidden=el.id!==`view-${view}`);
 document.querySelectorAll('[data-view]').forEach(el=>el.classList.toggle('active',el===button));
 $('#crumb').textContent=views[view][0];$('#page-title').textContent=views[view][1];
});
document.querySelectorAll('[data-filter]').forEach(button=>button.onclick=()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('selected',b===button));render();});
$('#search').oninput=render;$('#sort').onchange=render;
$('#sources').innerHTML=[['پونیشا','https://ponisha.ir'],['کارلنسر','https://www.karlancer.com'],['پارسکدرز','https://parscoders.com']].map(([name,url])=>`<article class="source-card"><span class="sample-tag">${name==='کارلنسر'?'پایش سروری · وضعیت اتصال بالای صفحه':'ورود دستی · اتصال خودکار غیرفعال'}</span><h3>${name}</h3><p>${name==='کارلنسر'?'پایشگر بدون ورود، صفحه عمومی پروژه‌ها را بررسی می‌کند. برای این مرحله نیازی به حساب ندارید.':'این منبع هنوز به پایشگر وصل نشده است.'} رمز و کوکی حساب خود را وارد کارنما نکنید.</p><a href="${url}" target="_blank" rel="noopener noreferrer">بازکردن سایت ↗</a></article>`).join('');
$('#save-settings').onclick=()=>{const value=Number($('#rate').value);if(!Number.isInteger(value)||value<10000||value>10000000)return toast('نرخ صحیح بین ۱۰ هزار تا ۱۰ میلیون تومان وارد کنید.');rate=value;localStorage.setItem('karnama-rate',rate);toast('نرخ ذخیره شد؛ برآورد آگهی‌های قبلی تغییر نمی‌کند.');};
$('#notifications').onclick=async()=>{if(!('Notification'in window))return toast('این مرورگر اعلان سیستمی ندارد؛ بخش «نیاز به شما» در دسترس است.');try{const result=await Notification.requestPermission();toast(result==='granted'?'اعلان هنگام باز بودن صفحه فعال شد.':'مجوز اعلان داده نشد؛ بخش «نیاز به شما» را بررسی کنید.');}catch(_){toast('اعلان در این پیش‌نمایش پشتیبانی نمی‌شود.')}};
$('#import-file').onclick=()=>$('#file').click();
$('#file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>900000)throw new Error('فایل باید کمتر از ۹۰۰ کیلوبایت باشد.');const items=JSON.parse(await file.text());if(!Array.isArray(items))throw new Error('فایل باید آرایه JSON از آگهی‌ها باشد.');await api('/api/jobs',items.map(item=>({...item,rate})));await reload();alertUser('آگهی‌ها وارد شدند؛ بازبینی شما لازم است.')}catch(error){toast(error instanceof SyntaxError?'ساختار JSON معتبر نیست.':error.message)}e.target.value='';};
function showDetail(id){
 const j=jobs.find(j=>j.id===Number(id));if(!j)return;selected=j.id;
 const proposal=`سلام، شرح پروژه «${j.title}» را بررسی کردم. برآورد اولیه من حدود ${fa(j.hours)} ساعت کار و ${fa(j.price)} تومان است. این پیشنهاد مشروط به بررسی نمونه‌ها، تأیید دامنه دقیق و معیار پذیرش است. هزینه سرویس‌های بیرونی و کارمزد جداگانه تعیین می‌شود. پیش‌نمایش فعلی فقط یک نمونه مفهومی است، نه پروژه تکمیل‌شده.`;
 const steps={review:['proposal','آماده‌کردن پیشنهاد'],proposal:['agreed','ثبت توافق انجام‌شده در سایت'],agreed:['execution','ساخت دستورکار اجرای Arena'],execution:['review_output','ثبت آماده‌شدن خروجی واقعی'],review_output:['delivered','ثبت تحویل انجام‌شده توسط من']};
 const step=steps[j.status];
 $('#detail').innerHTML=`<div class="modal-heading"><h2>${esc(j.title)}</h2><button class="close">×</button></div><div class="chips"><span class="chip">${statuses[j.status]}</span>${j.sample?'<span class="sample-tag">سفارش واقعی نیست</span>':''}</div><p class="detail-description">${esc(j.description)}</p><div class="detail-metrics"><div><small>قیمت پیشنهادی</small>${fa(j.price)} تومان</div><div><small>زمان پایه، نه موعد تحویل</small>${fa(j.hours)} ساعت</div><div><small>امتیاز قاعده‌محور، نه تضمین</small>${fa(j.score)} از ۱۰۰</div></div><p>تشخیص بر پایه کلمات کلیدی است. دسترسی به داده، مجوز ابزارها، سطح پیچیدگی و قابلیت اجرای واقعی در Arena باید جدا بررسی شود. برآورد شامل ۲۵٪ حاشیه عدم قطعیت است.</p>${j.url?`<a class="secondary" href="${esc(j.url)}" target="_blank" rel="noopener noreferrer">مشاهده آگهی اصلی ↗</a>`:''}<h3>پیش‌نمایش و بسته شروع</h3><p>${j.category==='وب و رابط کاربری'?'دمو یک لندینگ قالبی است و فقط عنوان و شرح آگهی را در طرح قرار می‌دهد.':'برای این دسته، پیش‌نمایش ساختار خروجی آماده می‌شود؛ داده واقعی پردازش نشده و محتوای سفارشی تولید نشده است.'}</p><div class="actions"><a class="secondary" target="_blank" rel="noopener" href="/api/jobs/${j.id}/demo">مشاهده دموی قالبی ↗</a><a class="secondary" href="/api/jobs/${j.id}/brief">دریافت دستورکار Arena ↓</a><a class="secondary" href="/api/jobs/${j.id}/package">بسته شروع ZIP ↓</a></div><h3>متن پیشنهادی برای کارفرما</h3><textarea id="proposal-text" rows="5" aria-label="متن پیشنهاد">${esc(proposal)}</textarea><button class="secondary" id="copy-proposal">کپی متن برای ارسال دستی</button><p class="subtle">کپی‌کردن به معنی ارسال نیست. ارسال پیشنهاد و ثبت توافق در سایت به عهده شماست.</p>${j.note?`<p class="detail-description">${esc(j.note)}</p>`:''}${step?`<label>یادداشت مرحله (برای توافق و تحویل الزامی)<textarea id="stage-note" rows="3" maxlength="4000" placeholder="دامنه توافق، مبلغ، موعد یا شواهد آزمون و تحویل؛ بدون اطلاعات محرمانه"></textarea></label><div class="actions"><button class="primary" data-transition="${step[0]}">${step[1]}</button><button class="secondary" data-transition="archived">بایگانی</button></div>`:j.status==='archived'?'<button class="secondary" data-transition="review">بازگرداندن به بررسی</button>':'<p>تحویل صرفاً بر اساس ثبت شما علامت خورده و از سایت کارفرما تأیید نشده است.</p>'}<p class="subtle">برای اجرای کار، فایل دستورکار را در گفت‌وگوی Arena وارد کنید. اتصال API اجرایی به Arena در این نسخه وجود ندارد.</p>`;
 if(!$('#detail-dialog').open)$('#detail-dialog').showModal();
}
document.addEventListener('click',async e=>{
 const button=e.target.closest('button');if(!button)return;
 if(button.matches('.close'))button.closest('dialog').close();
 if(button.hasAttribute('data-add'))openAdd();
 if(button.hasAttribute('data-detail'))showDetail(button.dataset.detail);
 if(button.hasAttribute('data-samples')){button.disabled=true;try{await api('/api/samples',{});await reload();toast('سه آگهی ساختگی برای آزمایش اضافه شد.')}catch(error){toast(error.message)}finally{button.disabled=false}}
 if(button.id==='copy-proposal'){try{await navigator.clipboard.writeText($('#proposal-text').value);toast('متن کپی شد؛ چیزی برای کارفرما ارسال نشده است.')}catch(_){$('#proposal-text').select();toast('متن را انتخاب و به‌صورت دستی کپی کنید.')}}
 if(button.hasAttribute('data-transition')){
 const target=button.dataset.transition;
 if(target==='delivered'&&!confirm('آیا خروجی واقعی را بازبینی و خودتان برای کارفرما ارسال کرده‌اید؟ این دکمه فقط وضعیت محلی را ثبت می‌کند.'))return;
 button.disabled=true;
 try{await api(`/api/jobs/${selected}`,{status:target,note:$('#stage-note')?.value||''});await reload();showDetail(selected);alertUser(target==='execution'?'دستورکار را دریافت و در Arena وارد کنید؛ کار خودکار شروع نشده است.':'وضعیت محلی ثبت شد؛ هیچ اقدام بیرونی انجام نشد.')}catch(error){toast(error.message)}finally{button.disabled=false}
 }
});
reload().catch(()=>{$('#jobs').innerHTML=empty('ارتباط با سرور برقرار نشد','صفحه را دوباره بارگذاری کنید؛ اطلاعات ساختگی نمایش داده نمی‌شود.');toast('دریافت اطلاعات ناموفق بود.');});

let monitorState = null, lastMonitorEvent = null;
const dateTime = ts => ts ? new Date(ts*1000).toLocaleString('fa-IR') : 'هنوز ثبت نشده';
async function refreshMonitor() {
 try {
  const state=await api('/api/monitor');monitorState=state;
  $('#monitor-message').textContent=state.message;
  $('#monitor-message').style.color=state.status==='error'?'#a95136':'';
  $('#monitor-time').textContent=`آخرین تلاش: ${dateTime(state.last_attempt)} · آخرین موفقیت: ${dateTime(state.last_success)} · نوبت بعد: ${state.enabled?dateTime(state.next_run):'متوقف'} · ایمیل: ${{not_configured:'تنظیم نشده',sent:'ارسال شد',failed:'ارسال ناموفق'}[state.email]||'—'}`;
  $('#toggle-monitor').textContent=state.enabled?'توقف پایش':'فعال‌کردن پایش';
  $('#scan-now').disabled=Boolean(state.running);
  const event=String(state.last_attempt)+state.status;
  if(lastMonitorEvent!==null && event!==lastMonitorEvent && state.status!=='running') {
    await reload();
    if(state.status==='error')alertUser('پایش کارلنسر به بررسی نیاز دارد: '+state.message);
    else if(state.added>0)alertUser(`${fa(state.added)} آگهی تازه دریافت شد؛ بازبینی شما لازم است.`);
  }
  lastMonitorEvent=event;
 } catch(error){$('#monitor-message').textContent='دریافت وضعیت پایش ناموفق بود؛ اتصال را بررسی کنید.';}
}
$('#scan-now').onclick=async()=>{try{await api('/api/monitor/scan',{});toast('بررسی در صف اجرا قرار گرفت.');await refreshMonitor();}catch(e){toast(e.message)}};
$('#toggle-monitor').onclick=async()=>{try{await api('/api/monitor/settings',{enabled:!monitorState?.enabled,rate});await refreshMonitor()}catch(e){toast(e.message)}};
const saveRate=$('#save-settings').onclick;
$('#save-settings').onclick=async()=>{saveRate();if(monitorState)try{await api('/api/monitor/settings',{enabled:monitorState.enabled,rate});}catch(e){toast('نرخ مرورگر ذخیره شد، اما نرخ پایشگر به‌روز نشد.')}};
let installPrompt;
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;});
$('#install-app').onclick=async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null;}else toast('در Chrome اندروید، این آدرس را مستقیماً باز کنید و از منوی سه‌نقطه «Install app / افزودن به صفحه اصلی» را بزنید. نصب داخل قاب پیش‌نمایش ممکن نیست.');};
if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
refreshMonitor();setInterval(()=>{if(!document.hidden)refreshMonitor();},15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){refreshMonitor();reload().catch(()=>{});}});
