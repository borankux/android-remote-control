package com.allin.cloudphone.inspector.relay

import android.os.Build
import org.json.JSONObject

object RelayPayloads {
    fun hello(deviceId: String, appVersion: String, rootAvailable: Boolean): String =
        JSONObject()
            .put("type", "hello")
            .put("deviceId", deviceId)
            .put("appVersion", appVersion)
            .put("manufacturer", Build.MANUFACTURER)
            .put("brand", Build.BRAND)
            .put("model", Build.MODEL)
            .put("device", Build.DEVICE)
            .put("androidVersion", Build.VERSION.RELEASE)
            .put("sdkInt", Build.VERSION.SDK_INT)
            .put("abis", Build.SUPPORTED_ABIS.joinToString(","))
            .put("rootAvailable", rootAvailable)
            .put("timestamp", System.currentTimeMillis())
            .toString()

    fun heartbeat(deviceId: String): String =
        JSONObject()
            .put("type", "heartbeat")
            .put("deviceId", deviceId)
            .put("timestamp", System.currentTimeMillis())
            .toString()
}
