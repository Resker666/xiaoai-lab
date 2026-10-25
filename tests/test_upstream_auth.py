from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from xiaoai_lab import upstream_auth


class SyntheticBackend:
    """The external account boundary; never sends a request."""

    def __init__(self, session, username, password, token_store=None, otp_callback=None):
        self.username = username
        self.password = password
        self.otp_callback = otp_callback
        self.response = {}
        self.succeed = False
        self.request_otp = False
        self.received_code = None

    async def _serviceLogin(self, uri, data=None):
        return self.response

    async def login(self, sid):
        await self._serviceLogin("serviceLoginAuth2", {})
        if self.request_otp:
            self.received_code = await self.otp_callback("Phone")
        return self.succeed


class AccountAdapterTests(unittest.IsolatedAsyncioTestCase):
    def make_account(self, **kwargs):
        account_class = upstream_auth.build_account_class(SyntheticBackend)
        return account_class(None, "PRIVATE_USER", "PRIVATE_PASSWORD", token_store=None, **kwargs)

    async def test_code_zero_challenge_is_not_treated_as_completed_login(self):
        account = self.make_account()
        account.response = {"code": 0, "notificationUrl": "https://account.xiaomi.com/verify?context=SECRET_CONTEXT", "securityStatus": 16, "passToken": "PRIVATE_TOKEN"}
        with self.assertRaises(upstream_auth.LoginNotComplete) as caught:
            await account.login("micoapi")
        self.assertEqual(caught.exception.reason, "verification_incomplete")
        self.assertEqual(caught.exception.code, 0)
        for secret in ("PRIVATE_USER", "PRIVATE_PASSWORD", "SECRET_CONTEXT", "PRIVATE_TOKEN", "notificationUrl"):
            self.assertNotIn(secret, str(caught.exception))

    async def test_failure_codes_are_classified_without_server_text(self):
        for code, expected in ((70016, "invalid_credentials"), (87001, "captcha_required"), (70022, "rate_limited"), (99999, "unexpected_response")):
            with self.subTest(code=code):
                account = self.make_account()
                account.response = {"code": code, "description": "PRIVATE_PASSWORD PRIVATE_TOKEN"}
                with self.assertRaises(upstream_auth.LoginNotComplete) as caught:
                    await account.login("micoapi")
                self.assertEqual(caught.exception.reason, expected)
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn("PRIVATE_", str(caught.exception))

    async def test_malformed_or_untrusted_code_does_not_leak_response(self):
        for response in (None, [], {"code": "PRIVATE_TOKEN"}, {"code": True}):
            with self.subTest(response=response):
                account = self.make_account()
                account.response = response
                with self.assertRaises(upstream_auth.LoginNotComplete) as caught:
                    await account.login("micoapi")
                self.assertEqual(caught.exception.reason, "unexpected_response")
                self.assertIsNone(caught.exception.code)
                self.assertNotIn("PRIVATE_TOKEN", str(caught.exception))

    async def test_successful_backend_verification_receives_callback(self):
        async def enter_code(method):
            self.assertEqual(method, "Phone")
            return "sample-code"

        account = self.make_account(otp_callback=enter_code)
        account.response = {"code": 0}
        account.request_otp = True
        account.succeed = True
        self.assertTrue(await account.login("micoapi"))
        self.assertEqual(account.received_code, "sample-code")

    async def test_new_attempt_does_not_reuse_previous_failure(self):
        account = self.make_account()
        account.response = {"code": 0, "notificationUrl": "PRIVATE_TOKEN"}
        with self.assertRaises(upstream_auth.LoginNotComplete):
            await account.login("micoapi")
        account.response = {"code": 99999}
        with self.assertRaises(upstream_auth.LoginNotComplete) as caught:
            await account.login("micoapi")
        self.assertEqual(caught.exception.reason, "unexpected_response")
        account.succeed = True
        self.assertTrue(await account.login("micoapi"))

    async def test_nonofficial_verification_address_is_rejected(self):
        for address in ("http://account.xiaomi.com/verify", "https://example.com/verify?context=PRIVATE_TOKEN", "//example.com/verify", "https://account.xiaomi.com:444/verify", "https://user:password@account.xiaomi.com/verify", "identity/authStart?context=PRIVATE_TOKEN", "HTTPS://account.xiaomi.com/verify"):
            with self.subTest(address=address):
                account = self.make_account()
                account.response = {"code": 0, "notificationUrl": address}
                with self.assertRaises(upstream_auth.LoginNotComplete) as caught:
                    await account.login("micoapi")
                self.assertEqual(caught.exception.reason, "untrusted_verification_url")
                self.assertNotIn(address, str(caught.exception))

    async def test_auth_failure_can_be_reported_to_the_launcher(self):
        failures = []
        account_class = upstream_auth.build_account_class(SyntheticBackend, on_failure=failures.append)
        account = account_class(None, "PRIVATE_USER", "PRIVATE_PASSWORD")
        account.response = {"code": 70016}
        with self.assertRaises(upstream_auth.LoginNotComplete):
            await account.login("micoapi")
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].reason, "invalid_credentials")


class DeviceQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_query_uses_environment_and_prints_only_selected_fields(self):
        context = AsyncMock()
        session = object()
        context.__aenter__.return_value = session
        session_factory = Mock(return_value=context)
        account = object()
        query = AsyncMock(return_value=[{"name": "sample-speaker", "model": "L05C", "deviceID": "sample-device", "online": True, "extra_private": "PRIVATE_TOKEN"}])
        native = SimpleNamespace(MiAccount=Mock(return_value=account), MiNAService=Mock(return_value=SimpleNamespace(device_list=query)))
        with patch.dict("sys.modules", {"aiohttp": SimpleNamespace(ClientSession=session_factory)}), patch.dict(os.environ, {"MI_USER": "PRIVATE_USER", "MI_PASS": "PRIVATE_PASSWORD"}), redirect_stdout(io.StringIO()) as output:
            code = await upstream_auth._list_devices(native)
        self.assertEqual(code, 0)
        native.MiAccount.assert_called_once_with(session, "PRIVATE_USER", "PRIVATE_PASSWORD")
        native.MiNAService.assert_called_once_with(account)
        query.assert_awaited_once_with()
        self.assertTrue(json.loads(output.getvalue())["devices"][0]["online"])
        self.assertNotIn("PRIVATE_", output.getvalue())
        context.__aexit__.assert_awaited_once()


class LauncherPreflightTests(unittest.TestCase):
    def call_main(self, args, environment):
        with patch.dict(os.environ, environment, clear=True), redirect_stderr(io.StringIO()) as stderr:
            result = upstream_auth.main(args)
        return result, stderr.getvalue()

    def make_upstream(self, root):
        (root / "main.py").touch()
        package = root / "src/xiaomi/miservice"
        package.mkdir(parents=True)
        (package / "__init__.py").touch()

    @patch("importlib.import_module")
    def test_missing_credentials_stop_before_optional_imports(self, import_module):
        code, message = self.call_main(["--list-devices"], {})
        self.assertEqual(code, 2)
        self.assertIn("MI_USER", message)
        import_module.assert_not_called()

    @patch("importlib.import_module")
    def test_placeholder_credentials_are_not_used_for_login(self, import_module):
        code, unused = self.call_main(["--list-devices"], {"MI_USER": "${MI_USER}", "MI_PASS": "${MI_PASS}"})
        self.assertEqual(code, 2)
        import_module.assert_not_called()

    @patch("importlib.import_module")
    def test_listener_requires_explicit_device_before_import(self, import_module):
        code, message = self.call_main([], {"MI_USER": "PRIVATE_USER", "MI_PASS": "PRIVATE_PASSWORD"})
        self.assertEqual(code, 2)
        self.assertIn("MI_DID", message)
        self.assertNotIn("PRIVATE_", message)
        import_module.assert_not_called()

    @patch("importlib.import_module")
    def test_invalid_upstream_directory_is_rejected(self, import_module):
        with tempfile.TemporaryDirectory() as tmp:
            code, message = self.call_main(["--list-devices", "--upstream", tmp], {"MI_USER": "PRIVATE_USER", "MI_PASS": "PRIVATE_PASSWORD"})
        self.assertEqual(code, 2)
        self.assertNotIn("PRIVATE_", message)
        import_module.assert_not_called()

    def test_listing_error_is_safe_and_never_enters_upstream_failure_guidance(self):
        original_cwd = Path.cwd()
        native = SimpleNamespace(MiAccount=None)
        modules = {
            "miservice": SimpleNamespace(__version__="3.0.2", MiAccount=SyntheticBackend),
            "src.xiaomi.miservice": native,
            "main": SimpleNamespace(main=lambda: self.fail("unsafe upstream failure guidance reached")),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_upstream(root)
            for error in (upstream_auth.LoginNotComplete("verification_incomplete", 0), RuntimeError("PRIVATE_TOKEN")):
                with self.subTest(error=type(error).__name__):
                    with patch("importlib.import_module", side_effect=lambda name: modules[name]), patch.object(upstream_auth, "_list_devices", AsyncMock(side_effect=error)):
                        code, message = self.call_main(["--list-devices", "--upstream", tmp], {"MI_USER": "PRIVATE_USER", "MI_PASS": "PRIVATE_PASSWORD"})
                    self.assertEqual(code, 1)
                    self.assertNotIn("PRIVATE_", message)
                    self.assertEqual(Path.cwd(), original_cwd)

    def test_listener_rejects_empty_or_conflicting_effective_device(self):
        for did in ("", "PRIVATE_OTHER_DEVICE"):
            with self.subTest(did=did), tempfile.TemporaryDirectory() as tmp:
                self.make_upstream(Path(tmp))
                entrypoint = SimpleNamespace(
                    get_config=lambda: SimpleNamespace(xiaomi=SimpleNamespace(did=did)),
                    main=lambda: self.fail("listener started with wrong configured device"),
                )
                modules = {
                    "miservice": SimpleNamespace(__version__="3.0.2", MiAccount=SyntheticBackend),
                    "src.xiaomi.miservice": SimpleNamespace(MiAccount=None),
                    "main": entrypoint,
                }
                with patch("importlib.import_module", side_effect=lambda name: modules[name]):
                    code, message = self.call_main(["--upstream", tmp], {"MI_USER": "PRIVATE_USER", "MI_PASS": "PRIVATE_PASSWORD", "MI_DID": "PRIVATE_TARGET_DEVICE"})
                self.assertEqual(code, 2)
                self.assertIn("MI_DID", message)
                self.assertNotIn("PRIVATE_", message)

    def test_listener_catching_auth_error_still_returns_failure_exit_code(self):
        import asyncio

        native = SimpleNamespace(MiAccount=None)

        def run_listener():
            account = native.MiAccount(None, "PRIVATE_USER", "PRIVATE_PASSWORD")
            account.response = {"code": 70016}
            try:
                asyncio.run(account.login("micoapi"))
            except upstream_auth.LoginNotComplete:
                pass

        modules = {
            "miservice": SimpleNamespace(__version__="3.0.2", MiAccount=SyntheticBackend),
            "src.xiaomi.miservice": native,
            "main": SimpleNamespace(main=run_listener, get_config=lambda: SimpleNamespace(xiaomi=SimpleNamespace(did="PRIVATE_TARGET_DEVICE"))),
        }
        with tempfile.TemporaryDirectory() as tmp:
            self.make_upstream(Path(tmp))
            with patch("importlib.import_module", side_effect=lambda name: modules[name]):
                code, unused = self.call_main(["--upstream", tmp], {"MI_USER": "PRIVATE_USER", "MI_PASS": "PRIVATE_PASSWORD", "MI_DID": "PRIVATE_TARGET_DEVICE"})
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
