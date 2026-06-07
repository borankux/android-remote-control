import unittest

from cloudphone_operator.config import ConfigError, OperatorConfig


class ConfigTest(unittest.TestCase):
    def test_reads_env_and_redacts_secrets(self):
        config = OperatorConfig.from_env(
            {
                "CLOUDPHONE_RELAY_URL": "https://example.com/cloudphone-relay/",
                "CLOUDPHONE_RELAY_TOKEN": "token-1234567890",
                "CLOUDPHONE_DEVICE_ID": "device-a",
                "CLOUDPHONE_OPERATOR_API_KEY": "fake-model-key-1234567890",
                "CLOUDPHONE_OPERATOR_TOKEN": "operator-token-1234567890",
            }
        )
        self.assertEqual(config.relay_url, "https://example.com/cloudphone-relay")
        self.assertEqual(config.device_id, "device-a")
        safe = config.safe_dict()
        self.assertNotIn("token-1234567890", str(safe))
        self.assertNotIn("fake-model-key-1234567890", str(safe))
        self.assertNotIn("operator-token-1234567890", str(safe))
        self.assertIn("toke", safe["relayToken"])

    def test_missing_token_can_be_required(self):
        with self.assertRaises(ConfigError) as ctx:
            OperatorConfig.from_env({}, require_token=True)
        self.assertEqual(ctx.exception.code, "missing_relay_token")

    def test_missing_token_can_be_allowed(self):
        config = OperatorConfig.from_env({}, require_token=False)
        self.assertEqual(config.relay_token, "")


if __name__ == "__main__":
    unittest.main()
