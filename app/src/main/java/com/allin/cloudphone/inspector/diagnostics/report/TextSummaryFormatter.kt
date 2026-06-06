package com.allin.cloudphone.inspector.diagnostics.report

import com.allin.cloudphone.inspector.diagnostics.model.DiagnosticReport

object TextSummaryFormatter {
    fun format(report: DiagnosticReport): String = buildString {
        appendLine("云机体检")
        appendLine("生成时间: ${report.generatedAt}")
        appendLine("设备: ${report.deviceModel}")
        appendLine("系统: ${report.androidVersion} / SDK ${report.sdkInt}")
        appendLine("Root: ${if (report.root.rootAvailable) "可用" else "不可用"}")
        appendLine("权限: ${report.permissions.count { it.granted }}/${report.permissions.size} 已授权")
        appendLine("已安装 App: ${report.apps.size}")
        appendLine("网络: ${report.network?.status ?: "未测试"}")
    }.trim()
}
