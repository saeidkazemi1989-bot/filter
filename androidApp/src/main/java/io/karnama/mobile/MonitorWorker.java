package io.karnama.mobile;

import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Build;
import android.webkit.CookieManager;
import androidx.annotation.NonNull;
import androidx.work.*;
import org.json.JSONObject;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Fetches only our own server. Never logs into Karlancer or runs project work. */
public class MonitorWorker extends Worker {
    public MonitorWorker(@NonNull Context context,@NonNull WorkerParameters params){super(context,params);}
    @NonNull @Override public Result doWork(){
        Context context=getApplicationContext();SharedPreferences prefs=context.getSharedPreferences("settings",0);
        String base=prefs.getString("server","");if(!base.startsWith("https://"))return Result.success();
        HttpURLConnection connection=null;
        try{
            connection=(HttpURLConnection)new URL(base+"/api/monitor").openConnection();
            connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(15000);connection.setReadTimeout(15000);
            String cookie=CookieManager.getInstance().getCookie(base);if(cookie!=null)connection.setRequestProperty("Cookie",cookie);
            int code=connection.getResponseCode();String event,message;
            if(code==401){event="login";message="برای ادامه دریافت اعلان، وارد فضای کاری کارنما شوید.";}
            else if(code==200){
                ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                try(InputStream input=connection.getInputStream()){
                    byte[] buffer=new byte[4096];int n;
                    while((n=input.read(buffer))!=-1){if(bytes.size()+n>100000)return Result.failure();bytes.write(buffer,0,n);}
                }
                JSONObject state=new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
                String status=state.optString("status");
                if(status.equals("error")){event="error:"+state.optString("message");message="پایش کارلنسر به بررسی شما نیاز دارد. برنامه را باز کنید.";}
                else if(status.equals("ok")&&state.optInt("added")>0){event="new:"+state.optString("last_success");message="آگهی تازه برای بررسی در کارنما دریافت شده است.";}
                else return Result.success();
            }else return Result.retry();
            if(!event.equals(prefs.getString("last_event",""))){
                if(Build.VERSION.SDK_INT>=33&&context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return Result.success();
                NotificationManager manager=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
                manager.createNotificationChannel(new NotificationChannel("monitor","فرصت‌ها و اقدام‌های کارنما",NotificationManager.IMPORTANCE_DEFAULT));
                PendingIntent intent=PendingIntent.getActivity(context,0,new Intent(context,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
                Notification notice=new Notification.Builder(context,"monitor").setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("کارنما؛ نیاز به بررسی شما").setContentText(message).setContentIntent(intent).setAutoCancel(true).build();
                manager.notify(21,notice);prefs.edit().putString("last_event",event).apply();
            }
            return Result.success();
        }catch(Exception e){return Result.retry();}finally{if(connection!=null)connection.disconnect();}
    }
}
