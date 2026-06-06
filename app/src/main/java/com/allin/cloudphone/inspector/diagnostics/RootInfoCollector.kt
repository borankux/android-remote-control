package com.allin.cloudphone.inspector.diagnostics

import android.os.Build
import com.allin.cloudphone.inspector.diagnostics.model.RootInfo
import java.io.File

object RootInfoCollector {
    private val suPaths = listOf(
        "/system/bin/su",
        "/system/xbin/su",
        "/sbin/su",
        "/su/bin/su",
        "/vendor/bin/su",
        "/data/local/xbin/su",
        "/data/local/bin/su",
        "/data/local/su"
    )

    fun collect(): RootInfo {
        val started = System.currentTimeMillis()
        val signals = mutableListOf<String>()
        suPaths.filter { File(it).exists() }.forEach { signals += "su exists: $it" }
        if (Build.TAGS?.contains("test-keys") == true) signals += "build tags: test-keys"
        if (File("/sbin/.magisk").exists() || File("/data/adb/magisk").exists()) signals += "Magisk path exists"

        return try {
            val process = ProcessBuilder("su", "-c", "id")
                .redirectErrorStream(false)
                .start()
            val waiter = Thread { process.waitFor() }.apply { start() }
            waiter.join(3000)
            val finished = !waiter.isAlive
            if (!finished) {
                process.destroy()
                RootInfo(false, signals, null, "", "", elapsed(started), "su 执行超时")
            } else {
                val stdout = process.inputStream.bufferedReader().readText().trim()
                val stderr = process.errorStream.bufferedReader().readText().trim()
                val exitCode = process.exitValue()
                RootInfo(
                    rootAvailable = exitCode == 0 && stdout.contains("uid=0"),
                    staticSignals = signals,
                    suExitCode = exitCode,
                    suStdout = stdout,
                    suStderr = stderr,
                    durationMs = elapsed(started),
                    error = null
                )
            }
        } catch (error: Throwable) {
            RootInfo(false, signals, null, "", "", elapsed(started), error.message ?: error.javaClass.simpleName)
        }
    }

    private fun elapsed(started: Long) = System.currentTimeMillis() - started
}
