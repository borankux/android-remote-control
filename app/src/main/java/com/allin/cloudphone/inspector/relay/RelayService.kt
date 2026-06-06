package com.allin.cloudphone.inspector.relay

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Base64
import androidx.core.app.NotificationCompat
import com.allin.cloudphone.inspector.BuildConfig
import com.allin.cloudphone.inspector.MainActivity
import com.allin.cloudphone.inspector.R
import com.allin.cloudphone.inspector.diagnostics.RootInfoCollector
import org.json.JSONObject
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.InetSocketAddress
import java.net.Socket
import java.security.MessageDigest
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

class RelayService : Service() {
    private val mainHandler = Handler(Looper.getMainLooper())
    private val commandExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private val client = OkHttpClient.Builder()
        .pingInterval(20, TimeUnit.SECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private lateinit var deviceId: String

    override fun onCreate() {
        super.onCreate()
        deviceId = RelayDeviceId.raw(this)
        updateStatus("准备连接")
        startForeground(NOTIFICATION_ID, buildNotification("正在连接 Relay"))
        connect()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (webSocket == null) connect()
        return START_STICKY
    }

    override fun onDestroy() {
        webSocket?.close(1000, "service stopped")
        webSocket = null
        connected = false
        updateStatus("已停止")
        commandExecutor.shutdownNow()
        client.dispatcher.executorService.shutdown()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun connect() {
        val url = "${RelayConfig.baseUrl}/${RelayDeviceId.encoded(this)}?token=${RelayConfig.token}"
        val request = Request.Builder().url(url).build()
        updateStatus("连接中: $url")
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                connected = true
                updateStatus("已连接 Relay")
                refreshNotification("Relay 已连接")
                webSocket.send(
                    RelayPayloads.hello(
                        deviceId = deviceId,
                        appVersion = BuildConfig.VERSION_NAME,
                        rootAvailable = safeRootAvailable()
                    )
                )
                scheduleHeartbeat()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                updateStatus("收到服务器消息: ${text.take(80)}")
                handleServerMessage(webSocket, text)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                this@RelayService.webSocket = null
                connected = false
                updateStatus("连接失败: ${t.message ?: t.javaClass.simpleName}")
                refreshNotification("Relay 连接失败，准备重试")
                mainHandler.postDelayed({ connect() }, RECONNECT_DELAY_MS)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                this@RelayService.webSocket = null
                connected = false
                updateStatus("连接关闭: $code $reason")
            }
        })
    }

    private fun handleServerMessage(webSocket: WebSocket, text: String) {
        val json = try {
            JSONObject(text)
        } catch (_: Throwable) {
            return
        }
        val type = json.optString("type")
        if (type == "adb_tunnel_open") {
            val tunnelId = json.optString("tunnelId")
            if (tunnelId.isNotBlank()) openAdbTunnel(tunnelId)
            return
        }
        if (type != "command") return
        val commandId = json.optString("commandId")
        val command = json.optJSONObject("command") ?: JSONObject()
        val name = command.optString("name")
        val params = command.optJSONObject("params") ?: JSONObject()
        if (commandId.isBlank() || name.isBlank()) return
        commandExecutor.execute {
            val startedAt = System.currentTimeMillis()
            val result = try {
                executeCommand(name, params).put("durationMs", System.currentTimeMillis() - startedAt)
            } catch (error: Throwable) {
                JSONObject()
                    .put("ok", false)
                    .put("error", error.message ?: error.javaClass.simpleName)
                    .put("durationMs", System.currentTimeMillis() - startedAt)
            }
            val payload = JSONObject()
                .put("type", "command_result")
                .put("commandId", commandId)
                .put("ok", result.optBoolean("ok", false))
                .put("error", if (result.has("error")) result.optString("error") else JSONObject.NULL)
                .put("result", result)
                .toString()
            webSocket.send(payload)
            updateStatus("命令完成: $name")
        }
    }

    private fun executeCommand(name: String, params: JSONObject): JSONObject = when (name) {
        "ping" -> JSONObject()
            .put("ok", true)
            .put("deviceId", deviceId)
            .put("appVersion", BuildConfig.VERSION_NAME)
            .put("timestamp", System.currentTimeMillis())

        "snapshot" -> snapshot()
        "screencap" -> screencap(params)
        "tap" -> tap(params)
        "swipe" -> swipe(params)
        "long_press" -> longPress(params)
        "back" -> keyEvent("BACK", 4)
        "home" -> keyEvent("HOME", 3)
        "input_text" -> inputText(params)
        "clear_text" -> clearText(params)
        "launch_app" -> launchApp(params)
        "launch_xhs" -> launchXhs()
        "dump_ui" -> dumpUi()
        "wait_for_text" -> waitForText(params)
        "adb_enable" -> adbEnable()
        "adb_status" -> adbStatus()
        "adb_disable" -> adbDisable()
        "self_update" -> selfUpdate(params)
        else -> JSONObject()
            .put("ok", false)
            .put("error", "unsupported_command")
    }

    private fun snapshot(): JSONObject = JSONObject()
        .put("ok", true)
        .put("deviceId", deviceId)
        .put("manufacturer", Build.MANUFACTURER)
        .put("brand", Build.BRAND)
        .put("model", Build.MODEL)
        .put("device", Build.DEVICE)
        .put("androidVersion", Build.VERSION.RELEASE)
        .put("sdkInt", Build.VERSION.SDK_INT)
        .put("rootAvailable", safeRootAvailable())
        .put("display", fixedRootCommand("wm size; wm density"))
        .put("focus", fixedRootCommand("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|topResumedActivity' | head -20"))
        .put("activity", fixedRootCommand("dumpsys activity activities | grep -E 'topResumedActivity|ResumedActivity|mResumedActivity' | head -20"))

    private fun screencap(params: JSONObject): JSONObject {
        val bytes = fixedRootCommandBytes("screencap -p")
        val maxWidth = params.optInt("maxWidth", 0)
        val format = params.optString("format", "png").lowercase(Locale.US)
        val quality = params.optInt("quality", 90).coerceIn(10, 100)
        if (maxWidth <= 0 && format == "png") {
            return JSONObject()
                .put("ok", true)
                .put("mimeType", "image/png")
                .put("byteCount", bytes.size)
                .put("base64", Base64.encodeToString(bytes, Base64.NO_WRAP))
        }
        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            ?: throw IllegalStateException("screencap decode failed")
        val scaled = if (maxWidth > 0 && bitmap.width > maxWidth) {
            val targetHeight = (bitmap.height * (maxWidth.toFloat() / bitmap.width)).toInt().coerceAtLeast(1)
            Bitmap.createScaledBitmap(bitmap, maxWidth, targetHeight, true)
        } else {
            bitmap
        }
        val compressFormat = when (format) {
            "jpg", "jpeg" -> Bitmap.CompressFormat.JPEG
            "webp" -> Bitmap.CompressFormat.WEBP
            else -> Bitmap.CompressFormat.PNG
        }
        val compressed = ByteArrayOutputStream()
        scaled.compress(compressFormat, quality, compressed)
        val outputWidth = scaled.width
        val outputHeight = scaled.height
        if (scaled !== bitmap) scaled.recycle()
        bitmap.recycle()
        val compressedBytes = compressed.toByteArray()
        val mimeType = when (compressFormat) {
            Bitmap.CompressFormat.JPEG -> "image/jpeg"
            Bitmap.CompressFormat.WEBP -> "image/webp"
            else -> "image/png"
        }
        return JSONObject()
            .put("ok", true)
            .put("mimeType", mimeType)
            .put("byteCount", compressedBytes.size)
            .put("sourceByteCount", bytes.size)
            .put("width", outputWidth)
            .put("height", outputHeight)
            .put("format", format)
            .put("quality", quality)
            .put("maxWidth", maxWidth)
            .put("base64", Base64.encodeToString(compressedBytes, Base64.NO_WRAP))
    }

    private fun tap(params: JSONObject): JSONObject {
        val x = params.optInt("x", -1)
        val y = params.optInt("y", -1)
        if (x < 0 || y < 0 || x > 4096 || y > 4096) {
            return JSONObject().put("ok", false).put("error", "invalid_tap_coordinates")
        }
        fixedRootCommand("input tap $x $y")
        return JSONObject().put("ok", true).put("x", x).put("y", y)
    }

    private fun swipe(params: JSONObject): JSONObject {
        val x1 = params.optInt("x1", -1)
        val y1 = params.optInt("y1", -1)
        val x2 = params.optInt("x2", -1)
        val y2 = params.optInt("y2", -1)
        val durationMs = params.optInt("durationMs", 300).coerceIn(50, 5000)
        if (listOf(x1, y1, x2, y2).any { it < 0 || it > 4096 }) {
            return JSONObject().put("ok", false).put("error", "invalid_swipe_coordinates")
        }
        fixedRootCommand("input swipe $x1 $y1 $x2 $y2 $durationMs")
        return JSONObject()
            .put("ok", true)
            .put("x1", x1)
            .put("y1", y1)
            .put("x2", x2)
            .put("y2", y2)
            .put("durationMs", durationMs)
    }

    private fun longPress(params: JSONObject): JSONObject {
        val x = params.optInt("x", -1)
        val y = params.optInt("y", -1)
        val durationMs = params.optInt("durationMs", 800).coerceIn(300, 5000)
        if (x < 0 || y < 0 || x > 4096 || y > 4096) {
            return JSONObject().put("ok", false).put("error", "invalid_long_press_coordinates")
        }
        fixedRootCommand("input swipe $x $y $x $y $durationMs")
        return JSONObject().put("ok", true).put("x", x).put("y", y).put("durationMs", durationMs)
    }

    private fun keyEvent(name: String, code: Int): JSONObject {
        fixedRootCommand("input keyevent $code")
        return JSONObject().put("ok", true).put("key", name).put("code", code)
    }

    private fun launchXhs(): JSONObject {
        return launchPackage("com.xingin.xhs")
    }

    private fun launchApp(params: JSONObject): JSONObject {
        val packageName = params.optString("packageName")
        if (packageName !in ALLOWED_LAUNCH_PACKAGES) {
            return JSONObject().put("ok", false).put("error", "package_not_allowed")
        }
        return launchPackage(packageName)
    }

    private fun launchPackage(packageName: String): JSONObject {
        val output = fixedRootCommand(
            "monkey -p ${shellQuote(packageName)} -c android.intent.category.LAUNCHER 1"
        )
        return JSONObject().put("ok", true).put("packageName", packageName).put("output", output)
    }

    private fun inputText(params: JSONObject): JSONObject {
        val rawText = params.optString("text")
        if (rawText.length > MAX_INPUT_TEXT_CHARS) {
            return JSONObject().put("ok", false).put("error", "text_too_long")
        }
        val encoded = rawText.replace(" ", "%s")
        fixedRootCommand("input text ${shellQuote(encoded)}")
        return JSONObject().put("ok", true).put("charCount", rawText.length)
    }

    private fun clearText(params: JSONObject): JSONObject {
        val count = params.optInt("count", 80).coerceIn(1, 500)
        fixedRootCommand("input keyevent 123; for i in \$(seq 1 $count); do input keyevent 67; done")
        return JSONObject().put("ok", true).put("count", count)
    }

    private fun dumpUi(): JSONObject {
        val output = fixedRootCommand(
            "uiautomator dump /sdcard/cloudphone-window.xml >/dev/null 2>&1; " +
                "head -c 200000 /sdcard/cloudphone-window.xml"
        )
        return JSONObject()
            .put("ok", true)
            .put("format", "uiautomator_xml")
            .put("charCount", output.length)
            .put("xml", output)
    }

    private fun waitForText(params: JSONObject): JSONObject {
        val text = params.optString("text")
        val timeoutMs = params.optInt("timeoutMs", 5000).coerceIn(500, 30_000)
        val intervalMs = params.optInt("intervalMs", 500).coerceIn(200, 5000)
        if (text.isBlank() || text.length > MAX_WAIT_TEXT_CHARS) {
            return JSONObject().put("ok", false).put("error", "invalid_text")
        }
        val deadline = System.currentTimeMillis() + timeoutMs
        var lastXml = ""
        while (System.currentTimeMillis() <= deadline) {
            lastXml = dumpUi().optString("xml")
            if (lastXml.contains(text)) {
                return JSONObject()
                    .put("ok", true)
                    .put("text", text)
                    .put("matched", true)
                    .put("xmlCharCount", lastXml.length)
            }
            Thread.sleep(intervalMs.toLong())
        }
        return JSONObject()
            .put("ok", false)
            .put("error", "text_not_found")
            .put("text", text)
            .put("matched", false)
            .put("xmlCharCount", lastXml.length)
    }

    private fun adbEnable(): JSONObject {
        val output = fixedRootCommand(
            "setprop service.adb.tcp.port 5555; stop adbd; start adbd; sleep 1; getprop service.adb.tcp.port"
        )
        return adbStatus().put("enableOutput", output)
    }

    private fun adbDisable(): JSONObject {
        val output = fixedRootCommand(
            "setprop service.adb.tcp.port -1; stop adbd; start adbd; sleep 1; getprop service.adb.tcp.port"
        )
        return adbStatus().put("disableOutput", output)
    }

    private fun adbStatus(): JSONObject {
        val prop = fixedRootCommand("getprop service.adb.tcp.port")
        val connectable = canConnectLocalAdb()
        return JSONObject()
            .put("ok", true)
            .put("host", ADB_HOST)
            .put("port", ADB_PORT)
            .put("serviceAdbTcpPort", prop)
            .put("connectable", connectable)
    }

    private fun canConnectLocalAdb(): Boolean = try {
        Socket().use { socket ->
            socket.connect(InetSocketAddress(ADB_HOST, ADB_PORT), 1000)
            true
        }
    } catch (_: Throwable) {
        false
    }

    private fun selfUpdate(params: JSONObject): JSONObject {
        val url = params.optString("url")
        val expectedSha256 = params.optString("sha256").lowercase(Locale.US)
        if (!isAllowedUpdateUrl(url)) {
            return JSONObject().put("ok", false).put("error", "update_url_not_allowed")
        }
        if (!expectedSha256.matches(Regex("^[a-f0-9]{64}$"))) {
            return JSONObject().put("ok", false).put("error", "invalid_sha256")
        }

        val request = Request.Builder().url(url).build()
        val response = client.newCall(request).execute()
        if (!response.isSuccessful) {
            return JSONObject().put("ok", false).put("error", "download_failed_${response.code}")
        }
        val bytes = response.body?.bytes() ?: ByteArray(0)
        if (bytes.isEmpty() || bytes.size > MAX_UPDATE_APK_BYTES) {
            return JSONObject()
                .put("ok", false)
                .put("error", "invalid_apk_size")
                .put("byteCount", bytes.size)
        }

        val actualSha256 = sha256(bytes)
        if (actualSha256 != expectedSha256) {
            return JSONObject()
                .put("ok", false)
                .put("error", "sha256_mismatch")
                .put("expected", expectedSha256)
                .put("actual", actualSha256)
        }

        val cacheApk = File(cacheDir, "cloudphone-update.apk")
        cacheApk.writeBytes(bytes)
        val stagingPath = "/data/local/tmp/cloudphone-inspector-update.apk"
        val logPath = "/data/local/tmp/cloudphone-inspector-update.log"
        val packageName = BuildConfig.APPLICATION_ID
        fixedRootCommand(
            "cp ${shellQuote(cacheApk.absolutePath)} ${shellQuote(stagingPath)}; " +
                "chmod 644 ${shellQuote(stagingPath)}; " +
                "(pm install -r ${shellQuote(stagingPath)} > ${shellQuote(logPath)} 2>&1; " +
                "install_code=\$?; " +
                "echo install_exit_code=\$install_code >> ${shellQuote(logPath)} 2>&1; " +
                "sleep 2; " +
                "if [ \$install_code -eq 0 ]; then " +
                "monkey -p ${shellQuote(packageName)} -c android.intent.category.LAUNCHER 1 >> ${shellQuote(logPath)} 2>&1; " +
                "fi) &"
        )

        return JSONObject()
            .put("ok", true)
            .put("url", url)
            .put("sha256", actualSha256)
            .put("byteCount", bytes.size)
            .put("stagingPath", stagingPath)
            .put("logPath", logPath)
            .put("status", "install_started")
    }

    private fun isAllowedUpdateUrl(url: String): Boolean {
        val uri = try {
            Uri.parse(url)
        } catch (_: Throwable) {
            return false
        }
        val path = uri.path.orEmpty()
        return uri.scheme == "https" &&
            uri.host == BuildConfig.UPDATE_HOST &&
            path.startsWith("/download/") &&
            path.endsWith(".apk")
    }

    private fun sha256(bytes: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
        return digest.joinToString("") { "%02x".format(it) }
    }

    private fun openAdbTunnel(tunnelId: String) {
        commandExecutor.execute {
            val tunnelUrl = RelayConfig.adbDeviceUrl(RelayDeviceId.encoded(this), tunnelId)
            val request = Request.Builder().url(tunnelUrl).build()
            val tcpSocket = Socket()
            val closed = AtomicBoolean(false)
            try {
                tcpSocket.connect(InetSocketAddress(ADB_HOST, ADB_PORT), 5000)
            } catch (error: Throwable) {
                updateStatus("ADB tunnel 连接 adbd 失败: ${error.message ?: error.javaClass.simpleName}")
                return@execute
            }
            client.newWebSocket(request, object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    updateStatus("ADB tunnel 已连接: $tunnelId")
                    Thread {
                        try {
                            val buffer = ByteArray(32 * 1024)
                            val input = tcpSocket.getInputStream()
                            while (!closed.get()) {
                                val read = input.read(buffer)
                                if (read < 0) break
                                webSocket.send(ByteString.of(*buffer.copyOf(read)))
                            }
                        } catch (_: Throwable) {
                        } finally {
                            if (closed.compareAndSet(false, true)) {
                                webSocket.close(1000, "tcp closed")
                                try { tcpSocket.close() } catch (_: Throwable) {}
                            }
                        }
                    }.start()
                }

                override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                    try {
                        tcpSocket.getOutputStream().write(bytes.toByteArray())
                        tcpSocket.getOutputStream().flush()
                    } catch (_: Throwable) {
                        if (closed.compareAndSet(false, true)) {
                            webSocket.close(1011, "tcp write failed")
                            try { tcpSocket.close() } catch (_: Throwable) {}
                        }
                    }
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    if (closed.compareAndSet(false, true)) {
                        try { tcpSocket.close() } catch (_: Throwable) {}
                    }
                    updateStatus("ADB tunnel 失败: ${t.message ?: t.javaClass.simpleName}")
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    if (closed.compareAndSet(false, true)) {
                        try { tcpSocket.close() } catch (_: Throwable) {}
                    }
                    updateStatus("ADB tunnel 已关闭: $code")
                }
            })
        }
    }

    private fun fixedRootCommand(command: String): String {
        val output = fixedRootCommandBytes(command)
        return output.toString(Charsets.UTF_8).trim()
    }

    private fun fixedRootCommandBytes(command: String): ByteArray {
        val process = ProcessBuilder("su", "-c", command)
            .redirectErrorStream(true)
            .start()
        val output = ByteArrayOutputStream()
        process.inputStream.use { it.copyTo(output) }
        val exitCode = process.waitFor()
        if (exitCode != 0) {
            throw IllegalStateException("fixed command failed: $exitCode")
        }
        return output.toByteArray()
    }

    private fun shellQuote(value: String): String =
        "'" + value.replace("'", "'\\''") + "'"

    private fun scheduleHeartbeat() {
        mainHandler.postDelayed(object : Runnable {
            override fun run() {
                val socket = webSocket ?: return
                socket.send(RelayPayloads.heartbeat(deviceId))
                updateStatus("已连接 Relay，心跳 ${System.currentTimeMillis()}")
                mainHandler.postDelayed(this, HEARTBEAT_MS)
            }
        }, HEARTBEAT_MS)
    }

    private fun safeRootAvailable(): Boolean = try {
        RootInfoCollector.collect().rootAvailable
    } catch (_: Throwable) {
        false
    }

    private fun updateStatus(status: String) {
        latestStatus = status
    }

    private fun refreshNotification(text: String) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun buildNotification(text: String): Notification {
        ensureChannel()
        val intent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(text)
            .setContentIntent(intent)
            .setOngoing(true)
            .build()
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Cloudphone Relay",
            NotificationManager.IMPORTANCE_LOW
        )
        manager.createNotificationChannel(channel)
    }

    companion object {
        private const val CHANNEL_ID = "cloudphone_relay"
        private const val NOTIFICATION_ID = 2401
        private const val HEARTBEAT_MS = 15_000L
        private const val RECONNECT_DELAY_MS = 5_000L
        private const val ACTION_STOP = "com.allin.cloudphone.inspector.relay.STOP"
        private const val MAX_INPUT_TEXT_CHARS = 200
        private const val MAX_WAIT_TEXT_CHARS = 80
        private const val MAX_UPDATE_APK_BYTES = 80 * 1024 * 1024
        private const val ADB_HOST = "localhost"
        private const val ADB_PORT = 5555
        private val ALLOWED_LAUNCH_PACKAGES = setOf(
            "com.xingin.xhs",
            "com.allin.cloudphone.inspector"
        )

        @Volatile
        var latestStatus: String = "未启动"
            private set

        @Volatile
        var connected: Boolean = false
            private set

        fun start(context: Context) {
            try {
                val intent = Intent(context, RelayService::class.java)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            } catch (error: Throwable) {
                latestStatus = "启动失败: ${error.message ?: error.javaClass.simpleName}"
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, RelayService::class.java).setAction(ACTION_STOP)
            context.startService(intent)
        }
    }
}
