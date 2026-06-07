package com.allin.cloudphone.inspector.diagnostics.network

import com.allin.cloudphone.inspector.diagnostics.model.NetworkCheckResult
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.Socket
import java.net.URL
import javax.net.ssl.HttpsURLConnection

object NetworkCollector {
    fun check(input: String, timeoutMs: Int = 5000): NetworkCheckResult {
        val started = System.currentTimeMillis()
        return try {
            val target = NetworkTargetParser.parse(input)
            val addresses = InetAddress.getAllByName(target.host).map { it.hostAddress ?: it.hostName }

            Socket().use { socket ->
                socket.connect(java.net.InetSocketAddress(target.host, target.port), timeoutMs)
            }

            val http = target.httpUrl?.let { url -> checkHttp(url, timeoutMs) }
            NetworkCheckResult(
                input = input,
                status = "OK",
                host = target.host,
                port = target.port,
                resolvedAddresses = addresses,
                tcpConnected = true,
                httpStatus = http?.first,
                tlsProtocol = http?.second,
                durationMs = elapsed(started),
                error = null
            )
        } catch (error: Throwable) {
            NetworkCheckResult(
                input = input,
                status = "FAILED",
                host = null,
                port = null,
                resolvedAddresses = emptyList(),
                tcpConnected = false,
                httpStatus = null,
                tlsProtocol = null,
                durationMs = elapsed(started),
                error = error.message ?: error.javaClass.simpleName
            )
        }
    }

    private fun checkHttp(rawUrl: String, timeoutMs: Int): Pair<Int, String?> {
        val connection = URL(rawUrl).openConnection() as HttpURLConnection
        connection.connectTimeout = timeoutMs
        connection.readTimeout = timeoutMs
        connection.requestMethod = "GET"
        connection.instanceFollowRedirects = false
        return try {
            val status = connection.responseCode
            val tls = (connection as? HttpsURLConnection)?.cipherSuite
            status to tls
        } finally {
            connection.disconnect()
        }
    }

    private fun elapsed(started: Long) = System.currentTimeMillis() - started
}
