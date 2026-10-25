"""Offline contract tests, additionally run in the prepared M1 environment."""

import logging
import io
import unittest
from unittest.mock import AsyncMock, patch

from xiaoai_lab.upstream_auth import LoginNotComplete, build_account_class

try:
    from miservice import MiAccount as BackendAccount
except ImportError:
    BackendAccount = None


@unittest.skipIf(BackendAccount is None, "requires the pinned optional MiService backend")
class OptionalBackendContractTests(unittest.IsolatedAsyncioTestCase):
    def make_account(self):
        async def enter_code(method):
            self.assertEqual(method, "Phone")
            return "sample-code"

        account_class = build_account_class(BackendAccount)
        return account_class(object(), "sample-user", "sample-password", token_store=None, otp_callback=enter_code)

    def responses(self):
        initial = {"code": 70016, "qs": "sample-qs", "sid": "micoapi", "_sign": "sample-sign", "callback": "https://account.xiaomi.com/sample"}
        challenge = {"code": 0, "notificationUrl": "/identity/authStart?context=sample-context", "securityStatus": 16, "captchaUrl": None}
        complete = {"code": 0, "userId": "sample-user-id", "passToken": "sample-pass-token", "location": "https://account.xiaomi.com/sample", "nonce": 1, "ssecurity": "sample-security"}
        return initial, challenge, complete

    async def test_code_zero_challenge_delegates_to_real_backend_verification(self):
        account = self.make_account()
        initial, challenge, complete = self.responses()

        async def verify(sid, notification):
            self.assertEqual(await account.otp_callback("Phone"), "sample-code")
            return complete

        account._verify_otp = AsyncMock(side_effect=verify)
        account._securityTokenService = AsyncMock(return_value="sample-service-token")
        with patch.object(BackendAccount, "_serviceLogin", AsyncMock(side_effect=[initial, challenge])):
            self.assertTrue(await account.login("micoapi"))
        account._verify_otp.assert_awaited_once_with("micoapi", "/identity/authStart?context=sample-context")
        self.assertEqual(account.token["micoapi"], ("sample-security", "sample-service-token"))

    async def test_real_backend_failure_does_not_emit_raw_challenge_or_username(self):
        account = self.make_account()
        initial, challenge, unused = self.responses()
        account._verify_otp = AsyncMock(side_effect=RuntimeError("PRIVATE_TOKEN SECRET_CONTEXT sample-user"))
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        logger = logging.getLogger("miservice")
        logger.addHandler(handler)
        try:
            with patch.object(BackendAccount, "_serviceLogin", AsyncMock(side_effect=[initial, challenge])):
                with self.assertRaises(LoginNotComplete) as caught:
                    await account.login("micoapi")
            self.assertEqual(caught.exception.reason, "verification_incomplete")
            combined = str(caught.exception) + captured.getvalue()
            for secret in ("PRIVATE_TOKEN", "SECRET_CONTEXT", "sample-user", "sample-context"):
                self.assertNotIn(secret, combined)
        finally:
            logger.removeHandler(handler)
            handler.close()

    async def test_initial_unauthenticated_response_does_not_imply_wrong_password(self):
        account = self.make_account()
        initial, unused, unused_complete = self.responses()
        with patch.object(BackendAccount, "_serviceLogin", AsyncMock(side_effect=[initial, TimeoutError("PRIVATE_TOKEN")])):
            with self.assertRaises(LoginNotComplete) as caught:
                await account.login("micoapi")
        self.assertEqual(caught.exception.reason, "unexpected_response")
        self.assertNotIn("PRIVATE_TOKEN", str(caught.exception))

    async def test_cached_account_retains_native_service_request_contract(self):
        account = self.make_account()
        account.token = {"userId": "sample-user-id", "micoapi": ("sample-security", "sample-service-token")}

        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def json(self, **kwargs):
                return {"code": 0, "data": [{"deviceID": "sample-device", "hardware": "L05C", "online": True}]}

        with patch.object(account, "request", return_value=Response()):
            result = await account.mi_request("micoapi", "https://api2.mina.mi.com/sample", None, {})
        self.assertEqual(result["data"][0]["deviceID"], "sample-device")
        self.assertTrue(result["data"][0]["online"])


if __name__ == "__main__":
    unittest.main()
