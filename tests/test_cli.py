import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from xiaoai_lab.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = main(args)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    @patch("urllib.request.OpenerDirector.open", side_effect=OSError("offline"))
    def test_doctor_stdout_is_json_even_when_ollama_is_offline(self, unused):
        code, output, error = self.run_cli(["doctor", "--timeout", "0.2"])
        self.assertEqual((code, error), (0, ""))
        report = json.loads(output)
        self.assertEqual(report["ollama"]["status"], "unavailable")
        self.assertFalse(report["device_tested"])

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_probe_custom_ports_timeout_and_json(self, connect):
        code, output, error = self.run_cli(["probe", "--ip", "192.168.1.105", "--ports", "443,80,443", "--timeout", "0.25"])
        self.assertEqual((code, error), (0, ""))
        report = json.loads(output)
        self.assertEqual([r["port"] for r in report["results"]], [443, 80])
        self.assertEqual(connect.call_args_list[0].args, (("192.168.1.105", 443),))
        self.assertEqual(connect.call_args_list[0].kwargs, {"timeout": 0.25})

    @patch("xiaoai_lab.diagnostics.socket.create_connection", side_effect=TimeoutError())
    def test_no_open_ports_is_a_completed_diagnostic(self, unused):
        code, output, error = self.run_cli(["probe", "--ip", "192.168.1.105"])
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(all(r["status"] == "timeout" for r in json.loads(output)["results"]))

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_bad_probe_arguments_have_no_network_side_effects(self, connect):
        for extra in (["--ports", "80,0"], ["--ports", "80,abc"], ["--ports", ""], ["--ports", "80,"], ["--timeout", "nan"], ["--timeout", "inf"], ["--timeout", "0"]):
            with self.subTest(extra=extra):
                code, output, error = self.run_cli(["probe", "--ip", "192.168.1.105", *extra])
                self.assertEqual((code, output), (2, ""))
                self.assertTrue(error)
        connect.assert_not_called()

    @patch("urllib.request.OpenerDirector.open")
    def test_doctor_rejects_bad_url_and_timeout_without_http(self, open_http):
        for extra in (["--ollama-url", "http://user:password@localhost"], ["--timeout", "nan"]):
            code, output, error = self.run_cli(["doctor", *extra])
            self.assertEqual((code, output), (2, ""))
            self.assertNotIn("password", error)
        open_http.assert_not_called()

    @patch("urllib.request.OpenerDirector.open", side_effect=OSError("offline"))
    def test_output_creates_utf8_json_in_new_parent_directory(self, unused):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "实验记录" / "doctor.json"
            code, output, error = self.run_cli(["doctor", "--output", str(target)])
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), json.loads(output))
            self.assertFalse(target.read_bytes().startswith(b"\xef\xbb\xbf"))

    @patch("xiaoai_lab.diagnostics.socket.create_connection")
    def test_probe_report_contains_selected_target_and_results(self, unused):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "probe.json"
            code, output, error = self.run_cli(["probe", "--ip", "192.168.1.105", "--ports", "80", "--output", str(target)])
            self.assertEqual((code, error), (0, ""))
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved, json.loads(output))
            self.assertEqual(saved["target"], "192.168.1.105")

    @patch("urllib.request.OpenerDirector.open", side_effect=OSError("offline"))
    def test_output_never_overwrites_existing_record(self, unused):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "doctor.json"
            target.write_text("original", encoding="utf-8")
            code, output, error = self.run_cli(["doctor", "--output", str(target)])
            self.assertEqual((code, output), (1, ""))
            self.assertTrue(error)
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    @patch("urllib.request.OpenerDirector.open", side_effect=OSError("offline"))
    def test_output_io_errors_return_one_without_traceback(self, unused):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "not-a-directory"
            parent.write_text("existing", encoding="utf-8")
            code, output, error = self.run_cli(["doctor", "--output", str(parent / "doctor.json")])
            self.assertEqual((code, output), (1, ""))
            self.assertTrue(error)
            self.assertNotIn("Traceback", error)

    def test_command_required(self):
        code, output, error = self.run_cli([])
        self.assertEqual((code, output), (2, ""))
        self.assertTrue(error)

    def test_surrogate_from_http_cannot_break_utf8_stdout_or_export(self):
        for export in (False, True):
            with self.subTest(export=export), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "doctor.json"
                response = io.BytesIO(b'{"models": [{"name": "\\ud800"}]}')
                response.status = 200
                args = ["doctor", "--output", str(target)] if export else ["doctor"]
                with io.TextIOWrapper(io.BytesIO(), encoding="utf-8", write_through=True) as output:
                    with patch("urllib.request.OpenerDirector.open", return_value=response), redirect_stdout(output), redirect_stderr(io.StringIO()) as error:
                        code = main(args)
                    self.assertEqual((code, error.getvalue()), (0, ""))
                    report = json.loads(output.buffer.getvalue().decode("utf-8"))
                self.assertEqual(report["ollama"]["status"], "invalid_response")
                if export:
                    self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)

    def test_help_lists_m0_commands(self):
        code, output, error = self.run_cli(["--help"])
        self.assertEqual((code, error), (0, ""))
        self.assertIn("doctor", output)
        self.assertIn("probe", output)

    def test_subprocess_help_and_errors_are_utf8_on_english_windows(self):
        environment = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        for args, expected_code, channel in ((["--help"], 0, "stdout"), (["probe", "--ip", "8.8.8.8"], 2, "stderr")):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, "-m", "xiaoai_lab", *args], env=environment, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, expected_code, result.stderr)
                text = getattr(result, channel).decode("utf-8")
                self.assertTrue(any(ord(char) > 127 for char in text))
                self.assertNotIn("Traceback", text)


if __name__ == "__main__":
    unittest.main()
