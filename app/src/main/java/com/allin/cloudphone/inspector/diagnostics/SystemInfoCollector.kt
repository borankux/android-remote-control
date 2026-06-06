package com.allin.cloudphone.inspector.diagnostics

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import com.allin.cloudphone.inspector.diagnostics.model.KeyValueInfo
import java.io.File
import java.util.Locale
import java.util.TimeZone

object SystemInfoCollector {
    fun collect(context: Context): List<KeyValueInfo> {
        val battery = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val memory = ActivityManager.MemoryInfo().also {
            (context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).getMemoryInfo(it)
        }
        val dataStat = StatFs(Environment.getDataDirectory().absolutePath)

        return listOf(
            KeyValueInfo("厂商", Build.MANUFACTURER.orUnknown()),
            KeyValueInfo("品牌", Build.BRAND.orUnknown()),
            KeyValueInfo("型号", Build.MODEL.orUnknown()),
            KeyValueInfo("设备", Build.DEVICE.orUnknown()),
            KeyValueInfo("Android", "${Build.VERSION.RELEASE} / SDK ${Build.VERSION.SDK_INT}"),
            KeyValueInfo("安全补丁", if (Build.VERSION.SDK_INT >= 23) Build.VERSION.SECURITY_PATCH.orUnknown() else "N/A"),
            KeyValueInfo("指纹", Build.FINGERPRINT.orUnknown()),
            KeyValueInfo("ABI", Build.SUPPORTED_ABIS.joinToString()),
            KeyValueInfo("CPU 核心", Runtime.getRuntime().availableProcessors().toString()),
            KeyValueInfo("内存", "${memory.availMem.toMiB()} MiB 可用 / ${memory.totalMem.toMiB()} MiB 总计"),
            KeyValueInfo("Data 分区", "${dataStat.availableBytes.toGiB()} GiB 可用 / ${dataStat.totalBytes.toGiB()} GiB 总计"),
            KeyValueInfo("外部存储状态", Environment.getExternalStorageState()),
            KeyValueInfo("电量", batteryLevel(battery)),
            KeyValueInfo("时区", TimeZone.getDefault().id),
            KeyValueInfo("语言", Locale.getDefault().toLanguageTag())
        )
    }

    private fun batteryLevel(intent: Intent?): String {
        if (intent == null) return "未知"
        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        if (level < 0 || scale <= 0) return "未知"
        return "${level * 100 / scale}%"
    }

    private fun String?.orUnknown() = if (isNullOrBlank()) "未知" else this
    private fun Long.toMiB() = this / 1024L / 1024L
    private fun Long.toGiB() = this / 1024L / 1024L / 1024L
}
