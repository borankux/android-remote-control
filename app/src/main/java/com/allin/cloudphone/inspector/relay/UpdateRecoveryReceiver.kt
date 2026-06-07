package com.allin.cloudphone.inspector.relay

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class UpdateRecoveryReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        when (intent?.action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED -> RelayService.start(context.applicationContext)
            else -> return
        }
    }
}
