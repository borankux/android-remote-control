package com.allin.cloudphone.inspector.relay

import com.allin.cloudphone.inspector.BuildConfig

object RelayConfig {
    val baseUrl: String = BuildConfig.RELAY_URL
    val token: String = BuildConfig.RELAY_TOKEN

    fun adbDeviceUrl(encodedDeviceId: String, tunnelId: String): String =
        baseUrl.replace("/ws/device", "/adb/device") + "/$encodedDeviceId/$tunnelId?token=$token"
}
