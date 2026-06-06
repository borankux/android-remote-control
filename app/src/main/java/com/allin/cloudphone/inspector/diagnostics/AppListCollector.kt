package com.allin.cloudphone.inspector.diagnostics

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import com.allin.cloudphone.inspector.diagnostics.model.AppInfo

object AppListCollector {
    fun collect(context: Context): List<AppInfo> {
        val pm = context.packageManager
        val packages = if (Build.VERSION.SDK_INT >= 33) {
            pm.getInstalledPackages(PackageManager.PackageInfoFlags.of(0))
        } else {
            @Suppress("DEPRECATION")
            pm.getInstalledPackages(0)
        }
        return packages.map { pkg ->
            val appInfo = pkg.applicationInfo
            val label = appInfo?.loadLabel(pm)?.toString().orEmpty().ifBlank { pkg.packageName }
            AppInfo(
                label = label,
                packageName = pkg.packageName,
                versionName = pkg.versionName ?: "",
                versionCode = if (Build.VERSION.SDK_INT >= 28) pkg.longVersionCode else @Suppress("DEPRECATION") pkg.versionCode.toLong(),
                systemApp = appInfo?.flags?.and(ApplicationInfo.FLAG_SYSTEM) != 0,
                firstInstallTime = pkg.firstInstallTime,
                lastUpdateTime = pkg.lastUpdateTime
            )
        }.sortedWith(compareBy<AppInfo> { it.systemApp }.thenBy { it.label.lowercase() })
    }
}
