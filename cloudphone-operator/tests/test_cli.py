import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from cloudphone_operator.cli import main


class CliTest(unittest.TestCase):
    def test_help_command_outputs_capabilities_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["run", "帮助"])
        self.assertEqual(code, 0)
        self.assertIn("capabilities", output.getvalue())

    def test_devices_without_token_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["devices"])
        self.assertEqual(code, 1)
        self.assertIn("missing_relay_token", output.getvalue())


if __name__ == "__main__":
    unittest.main()
