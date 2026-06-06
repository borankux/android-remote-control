package com.allin.cloudphone.inspector

import com.allin.cloudphone.inspector.diagnostics.network.NetworkTargetParser
import org.junit.Assert.assertEquals
import org.junit.Test

class NetworkTargetParserTest {
    @Test
    fun parsesHttpsUrlWithExplicitPort() {
        val target = NetworkTargetParser.parse("https://api.example.com:8443/health")

        assertEquals("https", target.scheme)
        assertEquals("api.example.com", target.host)
        assertEquals(8443, target.port)
        assertEquals("https://api.example.com:8443/health", target.httpUrl)
    }

    @Test
    fun parsesHostAndPortAsTcpTargetWithoutHttpUrl() {
        val target = NetworkTargetParser.parse("tcp.example.com:9000")

        assertEquals(null, target.scheme)
        assertEquals("tcp.example.com", target.host)
        assertEquals(9000, target.port)
        assertEquals(null, target.httpUrl)
    }

    @Test
    fun defaultsBareHostToPort443() {
        val target = NetworkTargetParser.parse("example.com")

        assertEquals("example.com", target.host)
        assertEquals(443, target.port)
    }
}
