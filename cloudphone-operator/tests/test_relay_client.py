import unittest

from cloudphone_operator.config import OperatorConfig
from cloudphone_operator.relay_client import RelayClient, RelayError


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


class RelayClientTest(unittest.TestCase):
    def config(self):
        return OperatorConfig(relay_url="https://relay.test/cloudphone-relay", relay_token="token", device_id="device-a")

    def test_list_devices(self):
        def transport(method, path, headers, body, timeout):
            self.assertEqual(path, "/devices")
            self.assertEqual(headers["x-relay-token"], "token")
            return 200, '{"ok":true,"devices":[{"deviceId":"device-a","online":true}]}'

        client = RelayClient(self.config(), transport=transport)
        self.assertEqual(client.list_devices()[0]["deviceId"], "device-a")

    def test_send_command_polls_until_completed(self):
        calls = []

        def transport(method, path, headers, body, timeout):
            calls.append((method, path, body))
            if path == "/commands":
                return 200, '{"ok":true,"command":{"id":"cmd-1","status":"sent"}}'
            return 200, '{"ok":true,"command":{"id":"cmd-1","status":"completed","result":{"ok":true}}}'

        client = RelayClient(self.config(), transport=transport, sleeper=lambda _: None)
        command = client.send_command("device-a", "home", {})
        self.assertEqual(command["status"], "completed")
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[1][1], "/commands/cmd-1")

    def test_missing_token(self):
        client = RelayClient(OperatorConfig(relay_token=""), transport=lambda *args: (200, "{}"))
        with self.assertRaises(RelayError) as ctx:
            client.list_devices()
        self.assertEqual(ctx.exception.code, "missing_relay_token")

    def test_unauthorized_maps_to_code(self):
        client = RelayClient(self.config(), transport=lambda *args: (401, '{"ok":false,"error":"bad"}'))
        with self.assertRaises(RelayError) as ctx:
            client.list_devices()
        self.assertEqual(ctx.exception.code, "unauthorized")

    def test_invalid_json_maps_to_code(self):
        client = RelayClient(self.config(), transport=lambda *args: (200, "not-json"))
        with self.assertRaises(RelayError) as ctx:
            client.list_devices()
        self.assertEqual(ctx.exception.code, "invalid_relay_response")

    def test_wait_timeout_maps_to_code(self):
        def transport(method, path, headers, body, timeout):
            return 200, '{"ok":true,"command":{"id":"cmd-1","status":"sent"}}'

        clock = Clock()
        client = RelayClient(self.config(), transport=transport, sleeper=lambda _: None, monotonic=clock)
        with self.assertRaises(RelayError) as ctx:
            client.wait_command("cmd-1", timeout_ms=1)
        self.assertEqual(ctx.exception.code, "command_timeout")


if __name__ == "__main__":
    unittest.main()
