package io.azad.filter

import android.app.Application
import android.os.Handler
import android.os.Looper
import com.wireguard.android.backend.GoBackend
import com.wireguard.android.backend.Tunnel
import com.wireguard.config.Config
import java.io.ByteArrayInputStream
import java.util.concurrent.Executors

class VpnApp : Application() {
    lateinit var controller: VpnController
    override fun onCreate() { super.onCreate(); controller = VpnController(this) }
}

class VpnController(app: Application) {
    private val backend = GoBackend(app)
    private val store = ProfileStore(app)
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    var listener: (() -> Unit)? = null
    var busy = false; private set
    var hasProfile = store.exists(); private set
    var up = false; private set
    var message = "برای شروع، فایل تنظیمات سرور خود را وارد کنید."; private set
    private val tunnel = object : Tunnel {
        override fun getName() = "azad"
        override fun onStateChange(newState: Tunnel.State) {
            main.post { up = newState == Tunnel.State.UP; listener?.invoke() }
        }
    }
    private fun parse(text: String): Config {
        ProfilePolicy.check(text)
        return Config.parse(ByteArrayInputStream(text.toByteArray(Charsets.UTF_8)))
    }
    private fun runJob(success: String, failure: String, job: () -> Boolean) {
        if (busy) return
        busy = true
        listener?.invoke()
        worker.execute {
            try {
                val active = job()
                val saved = store.exists()
                main.post { up = active; hasProfile = saved; busy = false; message = success; listener?.invoke() }
            } catch (_: Exception) {
                // Never expose parser exceptions: they can contain private config values.
                val active = runCatching { backend.getState(tunnel) == Tunnel.State.UP }.getOrDefault(false)
                main.post { up = active; busy = false; message = failure; listener?.invoke() }
            }
        }
    }
    fun importProfile(read: () -> String) {
        if (up) return
        runJob("تنظیمات به‌صورت رمزگذاری‌شده روی دستگاه ذخیره شد.",
            "ورود ناموفق؛ فایل باید معتبر، دارای یک Peer، Endpoint، DNS و مسیر کامل IPv4 و IPv6 باشد.") {
            val text = read()
            parse(text)
            store.save(text)
            false
        }
    }
    fun connect() = runJob("تونل فعال است؛ دسترسی اینترنت و IP خروجی را جداگانه بررسی کنید.",
        "اتصال ناموفق؛ تنظیمات، مجوز VPN و دسترسی به سرور را بررسی کنید.") {
        backend.setState(tunnel, Tunnel.State.UP, parse(store.load())) == Tunnel.State.UP
    }
    fun disconnect() = runJob("تونل قطع شد. بدون مسدودسازی اندروید، اینترنت مستقیم در دسترس است.", "قطع تونل ناموفق بود؛ تنظیمات VPN اندروید را بررسی کنید.") {
        backend.setState(tunnel, Tunnel.State.DOWN, null) == Tunnel.State.UP
    }
    fun forget() {
        if (up) return
        runJob("تنظیمات از برنامه حذف شد؛ کلید را برای لغو دسترسی از سرور هم حذف کنید.", "حذف تنظیمات ناموفق بود.") { store.delete(); false }
    }
    fun refresh() = runJob("وضعیت تونل به‌روز شد. فعال بودن تونل به معنی دسترسی تأییدشده به اینترنت نیست.", "خواندن وضعیت ناموفق بود.") {
        backend.getState(tunnel) == Tunnel.State.UP
    }
}
