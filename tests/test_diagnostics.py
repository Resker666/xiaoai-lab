import io
import unittest
from unittest.mock import MagicMock, patch
from contextlib import redirect_stdout

from xiaoai_lab.cli import main
from xiaoai_lab.diagnostics import probe_tcp, validate_lan_ipv4, check_ollama


class LanInputTests(unittest.TestCase):
    def test_private_address(self):
        self.assertEqual(validate_lan_ipv4("192.168.1.105"), "192.168.1.105")
        self.assertEqual(validate_lan_ipv4("10.0.0.42"), "10.0.0.42")

    def test_external_address_rejected(self):
        for ip in ("8.8.8.8", "127.0.0.1", "169.254.0.3", "example.com", "fe80::1", "192.168.1.255"):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                validate_lan_ipv4(ip)

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_probe_reports_open_port(self, create_connection):
        sock = MagicMock()
        create_connection.return_value.__enter__.return_value = sock
        report = probe_tcp("192.168.1.105", (80,))
        self.assertEqual(report["results"], [{"port": 80, "status": "open"}])
        create_connection.assert_called_once_with(("192.168.1.105", 80), timeout=0.6)

    @patch("xiaoai_lab.diagnostics.socket.create_connection", side_effect=ConnectionRefusedError())
    def test_probe_reports_unreachable(self, unused):
        self.assertEqual(probe_tcp("192.168.1.105", (22,))["results"][0]["status"], "not_open_or_filtered")

    def test_cli_rejects_public_ip(self):
        with redirect_stdout(io.StringIO()) as output:
            code = main(["probe", "--ip", "8.8.8.8"])
        self.assertEqual(code, 2)
        self.assertIn("仅允许", output.getvalue())


class OllamaTests(unittest.TestCase):
    @patch("xiaoai_lab.diagnostics.urllib.request.urlopen", side_effect=OSError("down"))
    def test_offline_status(self, unused):
        self.assertEqual(check_ollama()["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
