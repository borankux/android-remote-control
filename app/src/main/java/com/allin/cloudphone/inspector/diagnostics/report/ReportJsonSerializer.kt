package com.allin.cloudphone.inspector.diagnostics.report

import com.allin.cloudphone.inspector.diagnostics.model.AppInfo
import com.allin.cloudphone.inspector.diagnostics.model.DiagnosticReport
import com.allin.cloudphone.inspector.diagnostics.model.KeyValueInfo
import com.allin.cloudphone.inspector.diagnostics.model.NetworkCheckResult
import com.allin.cloudphone.inspector.diagnostics.model.PermissionInfo
import com.allin.cloudphone.inspector.diagnostics.model.RootInfo

object ReportJsonSerializer {
    fun toJson(report: DiagnosticReport): String = buildString {
        append('{')
        field("generatedAt", report.generatedAt); comma()
        field("appVersion", report.appVersion); comma()
        field("deviceModel", report.deviceModel); comma()
        field("androidVersion", report.androidVersion); comma()
        field("sdkInt", report.sdkInt); comma()
        array("system", report.system, ::keyValueJson); comma()
        append("\"root\":"); append(rootJson(report.root)); comma()
        array("permissions", report.permissions, ::permissionJson); comma()
        array("apps", report.apps, ::appJson); comma()
        append("\"network\":")
        append(report.network?.let(::networkJson) ?: "null")
        append('}')
    }

    private fun keyValueJson(item: KeyValueInfo) =
        """{"label":${quote(item.label)},"value":${quote(item.value)}}"""

    private fun rootJson(root: RootInfo) = buildString {
        append('{')
        field("rootAvailable", root.rootAvailable); comma()
        array("staticSignals", root.staticSignals) { quote(it) }; comma()
        nullableField("suExitCode", root.suExitCode); comma()
        field("suStdout", root.suStdout); comma()
        field("suStderr", root.suStderr); comma()
        field("durationMs", root.durationMs); comma()
        nullableField("error", root.error)
        append('}')
    }

    private fun permissionJson(permission: PermissionInfo) =
        """{"name":${quote(permission.name)},"granted":${permission.granted},"type":${quote(permission.type)}}"""

    private fun appJson(app: AppInfo) = buildString {
        append('{')
        field("label", app.label); comma()
        field("packageName", app.packageName); comma()
        field("versionName", app.versionName); comma()
        field("versionCode", app.versionCode); comma()
        field("systemApp", app.systemApp); comma()
        field("firstInstallTime", app.firstInstallTime); comma()
        field("lastUpdateTime", app.lastUpdateTime)
        append('}')
    }

    private fun networkJson(network: NetworkCheckResult) = buildString {
        append('{')
        field("input", network.input); comma()
        field("status", network.status); comma()
        nullableField("host", network.host); comma()
        nullableField("port", network.port); comma()
        array("resolvedAddresses", network.resolvedAddresses) { quote(it) }; comma()
        field("tcpConnected", network.tcpConnected); comma()
        nullableField("httpStatus", network.httpStatus); comma()
        nullableField("tlsProtocol", network.tlsProtocol); comma()
        field("durationMs", network.durationMs); comma()
        nullableField("error", network.error)
        append('}')
    }

    private fun StringBuilder.field(name: String, value: String) {
        append(quote(name)).append(':').append(quote(value))
    }

    private fun StringBuilder.field(name: String, value: Int) {
        append(quote(name)).append(':').append(value)
    }

    private fun StringBuilder.field(name: String, value: Long) {
        append(quote(name)).append(':').append(value)
    }

    private fun StringBuilder.field(name: String, value: Boolean) {
        append(quote(name)).append(':').append(value)
    }

    private fun StringBuilder.nullableField(name: String, value: String?) {
        append(quote(name)).append(':').append(value?.let(::quote) ?: "null")
    }

    private fun StringBuilder.nullableField(name: String, value: Int?) {
        append(quote(name)).append(':').append(value ?: "null")
    }

    private fun <T> StringBuilder.array(name: String, values: List<T>, mapper: (T) -> String) {
        append(quote(name)).append(':')
        append(values.joinToString(prefix = "[", postfix = "]") { mapper(it) })
    }

    private fun StringBuilder.comma() {
        append(',')
    }

    private fun quote(value: String): String = buildString {
        append('"')
        value.forEach { char ->
            when (char) {
                '\\' -> append("\\\\")
                '"' -> append("\\\"")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> append(char)
            }
        }
        append('"')
    }
}
