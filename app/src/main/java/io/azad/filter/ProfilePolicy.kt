package io.azad.filter

/** Additional full-tunnel policy; WireGuard's Config parser validates keys and IP syntax. */
object ProfilePolicy {
    const val MAX_BYTES = 65536
    fun check(text: String) {
        require(text.toByteArray(Charsets.UTF_8).size <= MAX_BYTES) { "فایل تنظیمات بیش از حد بزرگ است." }
        var section = ""
        var peers = 0
        var endpoint = false
        var dns = false
        val routes = mutableSetOf<String>()
        for (raw in text.lineSequence()) {
            val line = raw.substringBefore('#').trim()
            if (line.startsWith("[")) {
                section = line.lowercase()
                if (section == "[peer]") peers++
                continue
            }
            val key = line.substringBefore('=').trim().lowercase()
            val value = line.substringAfter('=', "").trim()
            when {
                section == "[interface]" && key == "dns" -> dns = dns || value.isNotBlank()
                section == "[peer]" && key == "endpoint" -> endpoint = endpoint || value.isNotBlank()
                section == "[peer]" && key == "allowedips" -> routes.addAll(value.split(',').map { it.trim() })
            }
        }
        require(peers == 1) { "نسخه شخصی فقط یک Peer را می‌پذیرد." }
        require(endpoint) { "آدرس سرور (Endpoint) لازم است." }
        require(dns) { "برای این نسخه، DNS را در تنظیمات مشخص کنید." }
        require(routes.containsAll(setOf("0.0.0.0/0", "::/0"))) {
            "برای تونل کامل، AllowedIPs باید شامل 0.0.0.0/0 و ::/0 باشد."
        }
    }
}
