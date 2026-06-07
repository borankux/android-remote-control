package com.allin.cloudphone.inspector.diagnostics.model

data class DiagnosticReport(
    val generatedAt: String,
    val appVersion: String,
    val deviceModel: String,
    val androidVersion: String,
    val sdkInt: Int,
    val system: List<KeyValueInfo>,
    val root: RootInfo,
    val permissions: List<PermissionInfo>,
    val apps: List<AppInfo>,
    val network: NetworkCheckResult?
)

data class KeyValueInfo(
    val label: String,
    val value: String
)

data class RootInfo(
    val rootAvailable: Boolean,
    val staticSignals: List<String>,
    val suExitCode: Int?,
    val suStdout: String,
    val suStderr: String,
    val durationMs: Long,
    val error: String?
)

data class PermissionInfo(
    val name: String,
    val granted: Boolean,
    val type: String
)

data class AppInfo(
    val label: String,
    val packageName: String,
    val versionName: String,
    val versionCode: Long,
    val systemApp: Boolean,
    val firstInstallTime: Long,
    val lastUpdateTime: Long
)

data class NetworkCheckResult(
    val input: String,
    val status: String,
    val host: String?,
    val port: Int?,
    val resolvedAddresses: List<String>,
    val tcpConnected: Boolean,
    val httpStatus: Int?,
    val tlsProtocol: String?,
    val durationMs: Long,
    val error: String?
)
