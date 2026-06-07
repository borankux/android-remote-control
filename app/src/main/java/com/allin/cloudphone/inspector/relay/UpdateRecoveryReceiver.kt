package com.allin.cloudphone.inspector.relay

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class UpdateRecoveryReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        RelayService.start(context.applicationContext)
    }
}
