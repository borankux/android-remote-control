package com.allin.cloudphone.inspector.diagnostics

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.content.ContextCompat
import com.allin.cloudphone.inspector.diagnostics.model.PermissionInfo

object PermissionCollector {
    fun collect(context: Context): List<PermissionInfo> {
        val packageName = context.packageName
        val power = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val permissions = mutableListOf(
            normal("INTERNET", true),
            normal("ACCESS_NETWORK_STATE", true),
            manifest(context, Manifest.permission.REQUEST_INSTALL_PACKAGES),
            special("QUERY_ALL_PACKAGES", isManifestDeclared(context, "android.permission.QUERY_ALL_PACKAGES")),
            special("忽略电池优化", if (Build.VERSION.SDK_INT >= 23) power.isIgnoringBatteryOptimizations(packageName) else false),
            special("悬浮窗", if (Build.VERSION.SDK_INT >= 23) Settings.canDrawOverlays(context) else false)
        )
        if (Build.VERSION.SDK_INT >= 26) {
            permissions += special("安装未知来源应用", context.packageManager.canRequestPackageInstalls())
        }
        return permissions
    }

    private fun manifest(context: Context, permission: String) = PermissionInfo(
        name = permission.substringAfterLast('.'),
        granted = ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED ||
            isManifestDeclared(context, permission),
        type = "manifest"
    )

    private fun normal(name: String, granted: Boolean) = PermissionInfo(name, granted, "normal")
    private fun special(name: String, granted: Boolean) = PermissionInfo(name, granted, "special")

    private fun isManifestDeclared(context: Context, permission: String): Boolean = try {
        val info = context.packageManager.getPackageInfo(context.packageName, PackageManager.GET_PERMISSIONS)
        info.requestedPermissions?.contains(permission) == true
    } catch (_: Throwable) {
        false
    }

    fun appSettingsIntent(context: Context) = android.content.Intent(
        Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
        Uri.parse("package:${context.packageName}")
    )
}
