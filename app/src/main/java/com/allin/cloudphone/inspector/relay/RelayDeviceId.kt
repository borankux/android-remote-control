package com.allin.cloudphone.inspector.relay

import android.content.Context
import android.provider.Settings
import java.net.URLEncoder

object RelayDeviceId {
    fun raw(context: Context): String {
        val androidId = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ANDROID_ID
        ).orEmpty()
        return if (androidId.isBlank()) "unknown-device" else androidId
    }

    fun encoded(context: Context): String =
        URLEncoder.encode(raw(context), "UTF-8")
}
