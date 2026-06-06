package com.allin.cloudphone.inspector

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.allin.cloudphone.inspector.diagnostics.AppListCollector
import com.allin.cloudphone.inspector.diagnostics.PermissionCollector
import com.allin.cloudphone.inspector.diagnostics.RootInfoCollector
import com.allin.cloudphone.inspector.diagnostics.SystemInfoCollector
import com.allin.cloudphone.inspector.diagnostics.model.AppInfo
import com.allin.cloudphone.inspector.diagnostics.model.DiagnosticReport
import com.allin.cloudphone.inspector.diagnostics.model.KeyValueInfo
import com.allin.cloudphone.inspector.diagnostics.model.NetworkCheckResult
import com.allin.cloudphone.inspector.diagnostics.model.PermissionInfo
import com.allin.cloudphone.inspector.diagnostics.model.RootInfo
import com.allin.cloudphone.inspector.diagnostics.network.NetworkCollector
import com.allin.cloudphone.inspector.diagnostics.report.ReportJsonSerializer
import com.allin.cloudphone.inspector.diagnostics.report.TextSummaryFormatter
import com.allin.cloudphone.inspector.relay.RelayConfig
import com.allin.cloudphone.inspector.relay.RelayDeviceId
import com.allin.cloudphone.inspector.relay.RelayService
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    private lateinit var subtitleText: TextView
    private lateinit var statusPillText: TextView
    private lateinit var heroTitleText: TextView
    private lateinit var heroSubtitleText: TextView
    private lateinit var scoreText: TextView
    private lateinit var relayMetricText: TextView
    private lateinit var rootMetricText: TextView
    private lateinit var adbMetricText: TextView
    private lateinit var foregroundMetricText: TextView
    private lateinit var summaryText: TextView
    private lateinit var systemText: TextView
    private lateinit var rootText: TextView
    private lateinit var permissionText: TextView
    private lateinit var relayText: TextView
    private lateinit var networkText: TextView
    private lateinit var appText: TextView
    private lateinit var jsonText: TextView
    private lateinit var serverInput: EditText
    private lateinit var copyConnectionButton: Button
    private lateinit var relayToggleButton: Button
    private lateinit var detailsToggleButton: Button
    private lateinit var detailsContainer: View
    private val relayStatusTicker = object : Runnable {
        override fun run() {
            renderRelayStatus()
            mainHandler.postDelayed(this, 1000)
        }
    }

    private var latestReport: DiagnosticReport? = null
    private var latestNetwork: NetworkCheckResult? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        bindViews()
        copyConnectionButton.setOnClickListener { copyConnectionInfo() }
        findViewById<Button>(R.id.copyJsonButton).setOnClickListener { copyJson() }
        findViewById<Button>(R.id.refreshButton).setOnClickListener { refreshDiagnostics() }
        relayToggleButton.setOnClickListener { toggleRelay() }
        detailsToggleButton.setOnClickListener { toggleDetails() }
        findViewById<Button>(R.id.networkButton).setOnClickListener { runNetworkCheck() }

        RelayService.start(this)
        refreshDiagnostics()
        renderRelayStatus()
        mainHandler.post(relayStatusTicker)
    }

    override fun onDestroy() {
        mainHandler.removeCallbacks(relayStatusTicker)
        executor.shutdownNow()
        super.onDestroy()
    }

    private fun bindViews() {
        subtitleText = findViewById(R.id.subtitleText)
        statusPillText = findViewById(R.id.statusPillText)
        heroTitleText = findViewById(R.id.heroTitleText)
        heroSubtitleText = findViewById(R.id.heroSubtitleText)
        scoreText = findViewById(R.id.scoreText)
        relayMetricText = findViewById(R.id.relayMetricText)
        rootMetricText = findViewById(R.id.rootMetricText)
        adbMetricText = findViewById(R.id.adbMetricText)
        foregroundMetricText = findViewById(R.id.foregroundMetricText)
        summaryText = findViewById(R.id.summaryText)
        systemText = findViewById(R.id.systemText)
        rootText = findViewById(R.id.rootText)
        permissionText = findViewById(R.id.permissionText)
        relayText = findViewById(R.id.relayText)
        networkText = findViewById(R.id.networkText)
        appText = findViewById(R.id.appText)
        jsonText = findViewById(R.id.jsonText)
        serverInput = findViewById(R.id.serverInput)
        copyConnectionButton = findViewById(R.id.copyConnectionButton)
        relayToggleButton = findViewById(R.id.relayToggleButton)
        detailsToggleButton = findViewById(R.id.detailsToggleButton)
        detailsContainer = findViewById(R.id.detailsContainer)
    }

    private fun renderRelayStatus() {
        relayText.text = buildString {
            appendLine("设备 ID: ${RelayDeviceId.raw(this@MainActivity)}")
            appendLine("Relay: ${RelayConfig.baseUrl}")
            appendLine("状态: ${RelayService.latestStatus}")
        }.trim()
        relayToggleButton.text = if (relayConnected()) "停止 Relay" else "开启 Relay"
        latestReport?.let { renderStatusPanel(it) } ?: run {
            val relay = relayShortStatus()
            statusPillText.text = relay
            relayMetricText.text = relay
            setStatusColor(statusPillText, relay)
        }
    }

    private fun refreshDiagnostics() {
        setLoading("正在采集系统、Root、权限和应用列表...")
        executor.execute {
            val report = buildReport(latestNetwork)
            mainHandler.post {
                latestReport = report
                render(report)
            }
        }
    }

    private fun runNetworkCheck() {
        val input = serverInput.text.toString().trim()
        if (input.isEmpty()) {
            toast("请输入服务器地址")
            return
        }
        networkText.text = "正在测试 $input ..."
        executor.execute {
            val result = NetworkCollector.check(input)
            val report = buildReport(result)
            mainHandler.post {
                latestNetwork = result
                latestReport = report
                render(report)
            }
        }
    }

    private fun buildReport(network: NetworkCheckResult?): DiagnosticReport {
        val system = safeSystem()
        val root = safeRoot()
        val permissions = safePermissions()
        val apps = safeApps()
        val model = system.firstOrNull { it.label == "型号" }?.value ?: android.os.Build.MODEL.orEmpty()
        val androidVersion = system.firstOrNull { it.label == "Android" }?.value ?: android.os.Build.VERSION.RELEASE

        return DiagnosticReport(
            generatedAt = nowIso(),
            appVersion = BuildConfig.VERSION_NAME,
            deviceModel = model,
            androidVersion = androidVersion,
            sdkInt = android.os.Build.VERSION.SDK_INT,
            system = system,
            root = root,
            permissions = permissions,
            apps = apps,
            network = network
        )
    }

    private fun safeSystem(): List<KeyValueInfo> = try {
        SystemInfoCollector.collect(this)
    } catch (error: Throwable) {
        listOf(KeyValueInfo("机器信息", "采集失败: ${error.message ?: error.javaClass.simpleName}"))
    }

    private fun safePermissions(): List<PermissionInfo> = try {
        PermissionCollector.collect(this)
    } catch (_: Throwable) {
        emptyList()
    }

    private fun safeApps(): List<AppInfo> = try {
        AppListCollector.collect(this)
    } catch (_: Throwable) {
        emptyList()
    }

    private fun safeRoot(): RootInfo = try {
        RootInfoCollector.collect()
    } catch (error: Throwable) {
        RootInfo(
            rootAvailable = false,
            staticSignals = emptyList(),
            suExitCode = null,
            suStdout = "",
            suStderr = "",
            durationMs = 0,
            error = "Root 采集失败: ${error.message ?: error.javaClass.simpleName}"
        )
    }

    private fun render(report: DiagnosticReport) {
        renderStatusPanel(report)
        summaryText.text = TextSummaryFormatter.format(report)
        systemText.text = formatKeyValues(report.system)
        rootText.text = formatRoot(report.root)
        permissionText.text = formatPermissions(report.permissions)
        networkText.text = formatNetwork(report.network)
        appText.text = formatApps(report.apps)

        val json = ReportJsonSerializer.toJson(report)
        jsonText.text = if (json.length > 12000) {
            json.take(12000) + "\n... 已截断显示，复制 JSON 会复制完整内容 ..."
        } else {
            json
        }
    }

    private fun renderStatusPanel(report: DiagnosticReport) {
        val relay = relayShortStatus()
        val root = if (report.root.rootAvailable) "Ready" else "Unavailable"
        val adb = adbShortStatus()
        val foreground = foregroundShortStatus()
        val score = readinessScore(report)

        subtitleText.text = "App ${report.appVersion} · SDK ${report.sdkInt}"
        statusPillText.text = relay
        scoreText.text = score.toString()
        heroTitleText.text = when {
            !relayConnected() -> "Relay 未连接"
            report.root.rootAvailable -> getString(R.string.cloudphone_taken_over)
            else -> "需要处理 Root"
        }
        heroSubtitleText.text = "${report.deviceModel} · Android ${report.androidVersion}\n${statusDescription(report)}"
        relayMetricText.text = relay
        rootMetricText.text = root
        adbMetricText.text = adb
        foregroundMetricText.text = foreground

        setStatusColor(statusPillText, relay)
        setStatusColor(relayMetricText, relay)
        setStatusColor(rootMetricText, root)
        setStatusColor(adbMetricText, adb)
        setStatusColor(foregroundMetricText, foreground)
        scoreText.setTextColor(ContextCompat.getColor(this, scoreColor(score)))
    }

    private fun setLoading(message: String) {
        subtitleText.text = message
        statusPillText.text = "Collecting"
        heroTitleText.text = "正在采集"
        heroSubtitleText.text = "正在刷新系统、Root、权限和应用状态"
        scoreText.text = "--"
        relayMetricText.text = relayShortStatus()
        rootMetricText.text = "--"
        adbMetricText.text = "--"
        foregroundMetricText.text = "--"
        summaryText.text = "采集中..."
        systemText.text = ""
        rootText.text = ""
        permissionText.text = ""
        appText.text = ""
        jsonText.text = ""
    }

    private fun readinessScore(report: DiagnosticReport): Int {
        var score = 40
        if (report.root.rootAvailable) score += 25
        if (relayConnected()) score += 20
        val permissionTotal = report.permissions.size
        val granted = report.permissions.count { it.granted }
        if (permissionTotal == 0 || granted * 2 >= permissionTotal) score += 10
        if (report.network?.status == "OK") score += 5
        return score.coerceIn(0, 100)
    }

    private fun statusDescription(report: DiagnosticReport): String = when {
        !relayConnected() -> "启动 Relay 后即可接入远程控制台"
        report.root.rootAvailable -> "Root API 在线，Agent 可复制接入信息开始控制"
        else -> "Relay 在线，但 Root 控制能力不可用"
    }

    private fun relayConnected(): Boolean =
        RelayService.connected

    private fun relayShortStatus(): String = when {
        relayConnected() -> "Online"
        RelayService.latestStatus.contains("重试") -> "Retrying"
        RelayService.latestStatus.contains("失败") -> "Failed"
        RelayService.latestStatus.contains("停止") -> "Stopped"
        else -> "Unknown"
    }

    private fun adbShortStatus(): String = "Unknown"

    private fun foregroundShortStatus(): String = "Unknown"

    private fun scoreColor(score: Int): Int = when {
        score >= 80 -> R.color.ok
        score >= 60 -> R.color.warn
        else -> R.color.bad
    }

    private fun setStatusColor(view: TextView, status: String) {
        val color = when (status) {
            "Online", "Ready", "Bridge", "XHS" -> R.color.ok
            "Retrying", "Unknown", "--" -> R.color.unknown
            "Stopped" -> R.color.warn
            else -> R.color.bad
        }
        view.setTextColor(ContextCompat.getColor(this, color))
    }

    private fun formatKeyValues(values: List<KeyValueInfo>) =
        values.joinToString("\n") { "${it.label}: ${it.value}" }

    private fun formatRoot(root: RootInfo) = buildString {
        appendLine("状态: ${if (root.rootAvailable) "可用" else "不可用"}")
        appendLine("耗时: ${root.durationMs}ms")
        appendLine("静态信号: ${if (root.staticSignals.isEmpty()) "无" else root.staticSignals.joinToString()}")
        appendLine("su exitCode: ${root.suExitCode ?: "N/A"}")
        appendLine("stdout: ${root.suStdout.ifBlank { "N/A" }}")
        appendLine("stderr: ${root.suStderr.ifBlank { "N/A" }}")
        appendLine("error: ${root.error ?: "N/A"}")
    }.trim()

    private fun formatPermissions(permissions: List<PermissionInfo>) =
        permissions.joinToString("\n") { "${if (it.granted) "OK" else "受限"}  ${it.name} (${it.type})" }

    private fun formatNetwork(network: NetworkCheckResult?) = if (network == null) {
        "未测试。输入服务器地址后点击“测试连接”。"
    } else {
        buildString {
            appendLine("状态: ${network.status}")
            appendLine("输入: ${network.input}")
            appendLine("目标: ${network.host ?: "N/A"}:${network.port ?: "N/A"}")
            appendLine("DNS: ${network.resolvedAddresses.ifEmpty { listOf("N/A") }.joinToString()}")
            appendLine("TCP: ${if (network.tcpConnected) "已连接" else "失败"}")
            appendLine("HTTP: ${network.httpStatus ?: "N/A"}")
            appendLine("TLS/Cipher: ${network.tlsProtocol ?: "N/A"}")
            appendLine("耗时: ${network.durationMs}ms")
            appendLine("错误: ${network.error ?: "N/A"}")
        }.trim()
    }

    private fun formatApps(apps: List<AppInfo>) = buildString {
        appendLine("总数: ${apps.size}")
        apps.take(80).forEach { app ->
            val type = if (app.systemApp) "系统" else "用户"
            appendLine("$type  ${app.label}  ${app.packageName}  v${app.versionName} (${app.versionCode})")
        }
        if (apps.size > 80) appendLine("... 仅显示前 80 个，JSON 包含完整列表 ...")
    }.trim()

    private fun copyJson() {
        val report = latestReport ?: return toast("还没有报告")
        copy("云机体检 JSON", ReportJsonSerializer.toJson(report))
    }

    private fun copyConnectionInfo() {
        val report = latestReport
        val text = buildString {
            appendLine("Relay URL: ${relayHttpBaseUrl()}")
            appendLine("Relay WS: ${RelayConfig.baseUrl}")
            appendLine("Device ID: ${RelayDeviceId.raw(this@MainActivity)}")
            appendLine("Token header: x-relay-token")
            appendLine("Token: ${RelayConfig.token}")
            appendLine("App version: ${report?.appVersion ?: BuildConfig.VERSION_NAME}")
            appendLine("CLI:")
            appendLine("export CLOUDPHONE_RELAY_URL='${relayHttpBaseUrl()}'")
            appendLine("export CLOUDPHONE_RELAY_TOKEN='${RelayConfig.token}'")
            appendLine("export CLOUDPHONE_DEVICE_ID='${RelayDeviceId.raw(this@MainActivity)}'")
            appendLine("node tools/cloudphone-api-client.mjs devices")
        }.trim()
        copy("云机接入信息", text)
    }

    private fun toggleDetails() {
        val show = detailsContainer.visibility != View.VISIBLE
        detailsContainer.visibility = if (show) View.VISIBLE else View.GONE
        detailsToggleButton.text = getString(if (show) R.string.details_hide else R.string.details_show)
    }

    private fun toggleRelay() {
        if (relayConnected()) {
            RelayService.stop(this)
        } else {
            RelayService.start(this)
        }
        renderRelayStatus()
        latestReport?.let { renderStatusPanel(it) }
    }

    private fun relayHttpBaseUrl(): String =
        RelayConfig.baseUrl
            .replace("wss://", "https://")
            .replace("ws://", "http://")
            .removeSuffix("/ws/device")

    private fun copy(label: String, text: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        toast("已复制")
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun nowIso(): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date())
    }
}
