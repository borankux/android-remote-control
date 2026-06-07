package com.allin.cloudphone.inspector

import android.app.Application
import com.allin.cloudphone.inspector.relay.RelayService

class CloudPhoneApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        RelayService.start(this)
    }
}
