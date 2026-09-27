package io.karnama.mobile;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.CookieManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.*;
import androidx.work.*;
import java.net.URI;
import java.util.concurrent.TimeUnit;

public class MainActivity extends Activity {
    private WebView web;
    private String base;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (Build.VERSION.SDK_INT >= 33) requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 10);
        base=getSharedPreferences("settings",0).getString("server","");
        if(base.isEmpty()) configure(); else open();
    }
    private void configure() {
        LinearLayout layout=new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(32,70,32,32);layout.setFitsSystemWindows(true);
        TextView title=new TextView(this);title.setText("کارنما — اتصال به میزبان شما");title.setTextSize(23);layout.addView(title);
        TextView info=new TextView(this);info.setText("آدرس HTTPS سروری که کارنما روی آن نصب شده را وارد کنید. رمز کارلنسر لازم نیست. پایش روی میزبان انجام می‌شود؛ گوشی فقط نتایج را دریافت می‌کند.");info.setPadding(0,25,0,25);layout.addView(info);
        EditText address=new EditText(this);address.setSingleLine();address.setHint("https://karnama.example.com");address.setText(base);address.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);layout.addView(address);
        Button save=new Button(this);save.setText("اتصال امن");layout.addView(save);
        save.setOnClickListener(v->{
            try {
                URI uri=new URI(address.getText().toString().trim());
                if(!"https".equals(uri.getScheme()) || uri.getHost()==null || uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null || !(uri.getPath().isEmpty()||uri.getPath().equals("/"))) throw new Exception();
                String next="https://"+uri.getRawAuthority();
                WorkManager.getInstance(this).cancelUniqueWork("karnama-monitor");
                if(!next.equals(base))CookieManager.getInstance().removeAllCookies(null);
                base=next;getSharedPreferences("settings",0).edit().putString("server",base).remove("last_event").apply();open();
            }catch(Exception e){address.setError("آدرس معتبر HTTPS بدون مسیر یا اطلاعات ورود وارد کنید.");}
        });setContentView(layout);
    }
    private boolean sameOrigin(Uri uri) {
        Uri origin=Uri.parse(base);
        return "https".equals(uri.getScheme()) && origin.getHost().equals(uri.getHost()) && origin.getPort()==uri.getPort() && uri.getUserInfo()==null;
    }
    private void external(Uri uri) {
        if(!"https".equals(uri.getScheme()))return;
        try {startActivity(new Intent(Intent.ACTION_VIEW,uri));}catch(Exception e){Toast.makeText(this,"مرورگری برای بازکردن لینک پیدا نشد.",Toast.LENGTH_LONG).show();}
    }
    private void open() {
        LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setFitsSystemWindows(true);
        Button settings=new Button(this);settings.setText("کارنما  •  تغییر میزبان / تنظیم اتصال");settings.setOnClickListener(v->{if(web!=null){web.destroy();web=null;}configure();});layout.addView(settings);
        web=new WebView(this);web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
                if(sameOrigin(request.getUrl()))return false;
                external(request.getUrl());return true;
            }
            @Override public void onPageFinished(WebView view,String url){CookieManager.getInstance().flush();}
        });
        web.setDownloadListener((url,userAgent,disposition,type,length)->{
            Uri uri=Uri.parse(url);if(!sameOrigin(uri)) {external(uri);return;}
            try{
                DownloadManager.Request request=new DownloadManager.Request(uri);
                String cookie=CookieManager.getInstance().getCookie(base);if(cookie!=null)request.addRequestHeader("Cookie",cookie);
                request.setMimeType(type);request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                String file="karnama-"+System.currentTimeMillis()+(uri.getPath().endsWith("package")?".zip":".md");
                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,file);
                ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(request);
                Toast.makeText(this,"دانلود در پوشه Downloads آغاز شد.",Toast.LENGTH_LONG).show();
            }catch(Exception e){Toast.makeText(this,"دانلود ناموفق بود؛ از نسخه مرورگر استفاده کنید.",Toast.LENGTH_LONG).show();}
        });
        layout.addView(web,new LinearLayout.LayoutParams(-1,0,1));setContentView(layout);web.loadUrl(base+"/");
        PeriodicWorkRequest request=new PeriodicWorkRequest.Builder(MonitorWorker.class,30,TimeUnit.MINUTES)
            .setConstraints(new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build();
        WorkManager.getInstance(this).enqueueUniquePeriodicWork("karnama-monitor",ExistingPeriodicWorkPolicy.UPDATE,request);
    }
    @Override public void onBackPressed(){if(web!=null&&web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override protected void onDestroy(){if(web!=null)web.destroy();super.onDestroy();}
}
