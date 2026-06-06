package com.allin.cloudphone.inspector.diagnostics.network

import java.net.URI

data class NetworkTarget(
    val scheme: String?,
    val host: String,
    val port: Int,
    val httpUrl: String?
)

object NetworkTargetParser {
    fun parse(rawInput: String): NetworkTarget {
        val input = rawInput.trim()
        require(input.isNotEmpty()) { "请输入服务器地址" }

        if (input.startsWith("http://") || input.startsWith("https://")) {
            val uri = URI(input)
            val scheme = uri.scheme?.lowercase()
            val host = uri.host ?: throw IllegalArgumentException("无法解析主机名")
            val port = if (uri.port > 0) uri.port else if (scheme == "http") 80 else 443
            return NetworkTarget(scheme, host, port, input)
        }

        val lastColon = input.lastIndexOf(':')
        val hasSinglePort = lastColon > 0 && input.indexOf(':') == lastColon
        if (hasSinglePort) {
            val host = input.substring(0, lastColon).trim()
            val port = input.substring(lastColon + 1).toIntOrNull()
                ?: throw IllegalArgumentException("端口不是数字")
            require(host.isNotEmpty()) { "主机名为空" }
            require(port in 1..65535) { "端口超出范围" }
            return NetworkTarget(null, host, port, null)
        }

        return NetworkTarget(null, input, 443, null)
    }
}
