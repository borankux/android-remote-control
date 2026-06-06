package com.allin.cloudphone.inspector

import com.allin.cloudphone.inspector.diagnostics.model.AppInfo
import com.allin.cloudphone.inspector.diagnostics.model.DiagnosticReport
import com.allin.cloudphone.inspector.diagnostics.model.KeyValueInfo
import com.allin.cloudphone.inspector.diagnostics.model.NetworkCheckResult
import com.allin.cloudphone.inspector.diagnostics.model.PermissionInfo
import com.allin.cloudphone.inspector.diagnostics.model.RootInfo
import com.allin.cloudphone.inspector.diagnostics.report.ReportJsonSerializer
import com.allin.cloudphone.inspector.diagnostics.report.TextSummaryFormatter
import org.junit.Assert.assertTrue
import org.junit.Test

class ReportFormattersTest {
    @Test
    fun serializesReportAsEscapedJson() {
        val report = sampleReport(deviceModel = "Cloud \"Phone\"")

        val json = ReportJsonSerializer.toJson(report)

        assertTrue(json.contains("\"deviceModel\":\"Cloud \\\"Phone\\\"\""))
        assertTrue(json.contains("\"rootAvailable\":true"))
        assertTrue(json.contains("\"packageName\":\"com.example.app\""))
    }

    @Test
    fun textSummaryIncludesScreenshotCriticalFacts() {
        val summary = TextSummaryFormatter.format(sampleReport())

        assertTrue(summary.contains("云机体检"))
        assertTrue(summary.contains("Android 16"))
        assertTrue(summary.contains("Root: 可用"))
        assertTrue(summary.contains("已安装 App: 1"))
        assertTrue(summary.contains("网络: OK"))
    }

    private fun sampleReport(deviceModel: String = "Cloud Phone") = DiagnosticReport(
        generatedAt = "2026-06-06T04:00:00Z",
        appVersion = "0.1.0",
        deviceModel = deviceModel,
        androidVersion = "Android 16",
        sdkInt = 36,
        system = listOf(KeyValueInfo("ABI", "arm64-v8a")),
        root = RootInfo(
            rootAvailable = true,
            staticSignals = listOf("su found"),
            suExitCode = 0,
            suStdout = "uid=0(root)",
            suStderr = "",
            durationMs = 20,
            error = null
        ),
        permissions = listOf(PermissionInfo("INTERNET", true, "normal")),
        apps = listOf(AppInfo("Example", "com.example.app", "1.0", 1, false, 10, 20)),
        network = NetworkCheckResult(
            input = "https://example.com",
            status = "OK",
            host = "example.com",
            port = 443,
            resolvedAddresses = listOf("example-resolved-address"),
            tcpConnected = true,
            httpStatus = 200,
            tlsProtocol = "TLSv1.3",
            durationMs = 100,
            error = null
        )
    )
}
