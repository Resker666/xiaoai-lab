import errno
import io
import json
import os
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch
from contextlib import redirect_stderr

from xiaoai_lab.cli import main
from xiaoai_lab.diagnostics import doctor, probe_tcp, validate_lan_ipv4, check_ollama


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
        self.assertEqual(report["results"][0]["port"], 80)
        self.assertEqual(report["results"][0]["status"], "open")
        self.assertGreaterEqual(report["results"][0]["elapsed_ms"], 0)
        self.assertFalse(report["device_tested"])
        self.assertEqual(report["schema_version"], 1)
        self.assertIsNotNone(datetime.fromisoformat(report["recorded_at"]).tzinfo)
        create_connection.assert_called_once_with(("192.168.1.105", 80), timeout=0.6)

    @patch("xiaoai_lab.diagnostics.socket.create_connection", side_effect=ConnectionRefusedError(errno.ECONNREFUSED, "refused"))
    def test_probe_reports_unreachable(self, unused):
        self.assertEqual(probe_tcp("192.168.1.105", (22,))["results"][0]["status"], "closed")

    def test_cli_rejects_public_ip(self):
        with redirect_stderr(io.StringIO()) as output:
            code = main(["probe", "--ip", "8.8.8.8"])
        self.assertEqual(code, 2)
        self.assertIn("仅允许", output.getvalue())

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_invalid_port_list_never_partially_connects(self, connect):
        for ports in ((80, 0), (80, 65536), (), (True,), (80.5,), tuple(range(1, 34))):
            with self.subTest(ports=ports), self.assertRaises(ValueError):
                probe_tcp("192.168.1.105", ports)
        connect.assert_not_called()

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_invalid_timeout_never_connects(self, connect):
        for timeout in (0, -1, float("nan"), float("inf"), 10.1, True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                probe_tcp("192.168.1.105", (80,), timeout)
        connect.assert_not_called()

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_deduplicates_ports_and_preserves_order(self, connect):
        report = probe_tcp("172.16.0.42", (443, 80, 443), timeout=0.2)
        self.assertEqual([r["port"] for r in report["results"]], [443, 80])
        self.assertEqual(connect.call_count, 2)
        self.assertEqual(report["timeout_seconds"], 0.2)

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_probe_distinguishes_socket_outcomes_without_leaking_errors(self, connect):
        cases = [
            (TimeoutError(), "timeout"),
            (OSError(errno.ETIMEDOUT, "private details"), "timeout"),
            (OSError(errno.EHOSTUNREACH, "private details"), "unreachable"),
            (OSError(errno.ENETUNREACH, "private details"), "unreachable"),
            (OSError(errno.EACCES, "private details"), "permission_denied"),
            (OSError(10061, "private details"), "closed"),
            (OSError(10060, "private details"), "timeout"),
            (OSError(10065, "private details"), "unreachable"),
            (OSError("private details"), "error"),
        ]
        for error, expected in cases:
            with self.subTest(expected=expected, error=error.errno):
                connect.side_effect = error
                report = probe_tcp("192.168.1.105", (80,))
                self.assertEqual(report["results"][0]["status"], expected)
                self.assertNotIn("private details", json.dumps(report))

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_rejects_non_hosts_and_non_rfc1918_before_network(self, connect):
        for ip in ("192.168.1.0", "192.168.1.255", "172.15.1.1", "172.32.1.1", "100.64.0.1", "224.0.0.1", "0.0.0.0", "192.168.1.1/24"):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                probe_tcp(ip)
        connect.assert_not_called()


class OllamaTests(unittest.TestCase):
    @patch("urllib.request.OpenerDirector.open", side_effect=OSError("private details"))
    def test_offline_status(self, unused):
        self.assertEqual(check_ollama()["status"], "unavailable")

    def test_invalid_base_urls_rejected(self):
        for url in ("file:///etc/passwd", "ftp://localhost", "http://", "localhost:11434", "http://user:secret@localhost", "http://localhost:99999", "http://localhost/?token=secret", "http://localhost/#fragment", "http://localhost/\n"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                check_ollama(url)

    def test_invalid_timeout_rejected(self):
        for timeout in (0, -1, float("nan"), float("inf"), 10.1):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                check_ollama(timeout=timeout)


class TagsHandler(BaseHTTPRequestHandler):
    requests = []
    payload = b'{"models": []}'
    status = 200

    def do_GET(self):
        type(self).requests.append(self.path)
        self.send_response(type(self).status)
        self.send_header("Location", "/redirect-target")
        self.end_headers()
        try:
            self.wfile.write(type(self).payload)
        except (ConnectionError, OSError):
            pass

    def log_message(self, *args):
        pass


class OllamaHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), TagsHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        TagsHandler.requests = []
        TagsHandler.payload = b'{"models": []}'
        TagsHandler.status = 200

    def test_names_from_real_http_and_correct_path(self):
        TagsHandler.payload = json.dumps({"models": [{"name": "qwen-test:small", "model": "qwen-test:small", "size": 123, "details": {"family": "qwen"}}]}).encode()
        report = check_ollama(self.url + "/prefix/")
        self.assertEqual(report, {"status": "ok", "models": ["qwen-test:small"]})
        self.assertEqual(TagsHandler.requests, ["/prefix/api/tags"])

    def test_empty_model_list_is_healthy_but_not_inference(self):
        report = doctor(self.url, timeout=0.5)
        self.assertEqual(report["ollama"], {"status": "ok", "models": []})
        self.assertTrue(report["python_supported"])
        self.assertFalse(report["device_tested"])
        self.assertEqual(report["schema_version"], 1)
        self.assertTrue(report["tool_version"])

    def test_malformed_tags_never_crash_or_report_ok(self):
        for payload in (b"[]", b"null", b"{}", b'{"models": null}', b'{"models": {}}', b'{"models": [null]}', b'{"models": [{"name": 1}]}', b'{"models": [{}]}', b'{"models": [{"name": ""}]}', b"not json", b"\xff"):
            with self.subTest(payload=payload):
                TagsHandler.payload = payload
                self.assertEqual(check_ollama(self.url)["status"], "invalid_response")

    def test_oversized_body_is_rejected(self):
        TagsHandler.payload = b" " * (1024 * 1024 + 1)
        report = check_ollama(self.url)
        self.assertEqual(report["status"], "invalid_response")
        self.assertEqual(report["reason"], "response_too_large")

    def test_unpaired_unicode_surrogate_is_an_invalid_model_name(self):
        for name in ("\ud800", "\udfff"):
            with self.subTest(name=repr(name)):
                TagsHandler.payload = json.dumps({"models": [{"name": name}]}).encode("ascii")
                report = check_ollama(self.url)
                self.assertEqual(report["status"], "invalid_response")
                self.assertEqual(report["models"], [])

    def test_http_error_is_not_a_healthy_endpoint(self):
        TagsHandler.status = 503
        report = check_ollama(self.url)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["http_status"], 503)

    def test_redirect_is_not_followed(self):
        TagsHandler.status = 302
        report = check_ollama(self.url)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(TagsHandler.requests, ["/api/tags"])

    @patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1", "no_proxy": "", "NO_PROXY": ""})
    def test_local_diagnostics_ignore_environment_proxy(self):
        self.assertEqual(check_ollama(self.url)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
