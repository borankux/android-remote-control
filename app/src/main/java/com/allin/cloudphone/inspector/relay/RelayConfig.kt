package com.allin.cloudphone.inspector.relay

import com.allin.cloudphone.inspector.BuildConfig

object RelayConfig {
    val baseUrl: String = BuildConfig.RELAY_URL
    val token: String = BuildConfig.RELAY_TOKEN
    val configured: Boolean =
        baseUrl.isNotBlank() &&
            token.isNotBlank() &&
            !baseUrl.contains("relay.example.com")

    fun adbDeviceUrl(encodedDeviceId: String, tunnelId: String): String =
        baseUrl.replace("/ws/device", "/adb/device") + "/$encodedDeviceId/$tunnelId?token=$token"
}
