"""Optional XiaoAiAgent launcher using an existing interactive OTP backend.

No third-party imports or authentication requests occur when importing this
module. Run it with the separate XiaoAiAgent environment, not the M0 CLI env.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import importlib
import json
import logging
import os
from pathlib import Path
import sys
from typing import Callable
from urllib.parse import urljoin, urlsplit

from .device_binding import build_speaker_class


class LoginNotComplete(RuntimeError):
    def __init__(self, reason: str, code: int | None):
        self.reason = reason
        self.code = code
        descriptions = {
            "invalid_credentials": "小米账号或密码未通过验证",
            "captcha_required": "需要完成小米官方图片验证码验证",
            "rate_limited": "小米服务限制了登录请求，请稍后再试",
            "verification_incomplete": "小米身份验证尚未完成，请核对本机的短信或邮箱验证提示",
            "unexpected_response": "小米登录未完成，响应不符合当前适配器预期",
            "untrusted_verification_url": "验证地址不属于预期的小米官方 HTTPS 域名，已停止",
        }
        suffix = f" (code={code})" if code is not None else ""
        super().__init__(descriptions.get(reason, descriptions["unexpected_response"]) + suffix)


async def _read_otp(method: str) -> str:
    label = "邮箱" if method == "Email" else "短信"
    return (await asyncio.to_thread(getpass.getpass, f"输入小米{label}验证码（仅本机输入）：")).strip()


def _trusted_verification_url(value: object) -> bool:
    # Match the pinned backend's URL handling: it prepends ACCOUNT_BASE to
    # anything that does not start with lower-case 'http'.
    if (
        not isinstance(value, str)
        or not value.startswith(("https://", "/"))
        or any(ord(char) <= 32 or ord(char) == 127 or char == "\\" for char in value)
    ):
        return False
    try:
        parsed = urlsplit(urljoin("https://account.xiaomi.com", value))
        return (
            parsed.scheme == "https"
            and parsed.hostname == "account.xiaomi.com"
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def build_account_class(backend_class, on_failure: Callable[[LoginNotComplete], None] | None = None):
    """Delegate OTP to MiService, exposing only safe failure categories."""
    # The inspected backend includes raw responses in exception logs. Keep
    # those logs out of the terminal; our failure message never uses their text.
    logging.getLogger("miservice").setLevel(logging.CRITICAL)

    class VerifiedAccount(backend_class):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("otp_callback", _read_otp)
            super().__init__(*args, **kwargs)
            self._auth_code = None
            self._credential_response = False
            self._verification_requested = False
            self._url_rejected = False

        async def _serviceLogin(self, uri, data=None):
            response = await super()._serviceLogin(uri, data)
            if isinstance(response, dict):
                code = response.get("code")
                self._auth_code = code if type(code) is int and -1 <= code <= 999999 else None
                self._credential_response = uri.split("?", 1)[0] == "serviceLoginAuth2"
                notification = response.get("notificationUrl")
                if notification:
                    self._verification_requested = True
                    if not _trusted_verification_url(notification):
                        self._url_rejected = True
                        raise LoginNotComplete("untrusted_verification_url", self._auth_code)
            return response

        async def login(self, sid):
            self._auth_code = None
            self._credential_response = False
            self._verification_requested = False
            self._url_rejected = False
            try:
                authenticated = await super().login(sid)
            except LoginNotComplete as error:
                if on_failure is not None:
                    on_failure(error)
                raise
            if authenticated:
                return True
            if self._url_rejected:
                reason = "untrusted_verification_url"
            elif self._auth_code == 70016 and self._credential_response:
                reason = "invalid_credentials"
            elif self._auth_code in (87001, 70022):
                reason = {87001: "captcha_required", 70022: "rate_limited"}[self._auth_code]
            elif self._verification_requested:
                reason = "verification_incomplete"
            else:
                reason = "unexpected_response"
            error = LoginNotComplete(reason, self._auth_code)
            if on_failure is not None:
                on_failure(error)
            raise error

    return VerifiedAccount


def _configured(value: str | None) -> bool:
    return bool(value and value.strip() and not (value.strip().startswith("${") and value.strip().endswith("}")))


async def _list_devices(native) -> int:
    """Query through the existing service without upstream's unsafe error advice."""
    from aiohttp import ClientSession

    async with ClientSession() as session:
        account = native.MiAccount(session, os.environ["MI_USER"], os.environ["MI_PASS"])
        devices = await native.MiNAService(account).device_list()
    if not devices:
        print("未查询到设备；请在本机核对账号及音箱在线状态。", file=sys.stderr)
        return 1
    rows = [
        {
            "name": device.get("name"),
            "model": device.get("model"),
            "hardware": device.get("hardware"),
            "deviceID": device.get("deviceID") or device.get("did"),
            "online": device.get("online"),
        }
        for device in devices
    ]
    print(json.dumps({"devices": rows}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="使用独立 MiService 短信/邮箱验证启动 XiaoAiAgent")
    parser.add_argument("--upstream", type=Path, default=Path.cwd(), help="独立 XiaoAiAgent 仓库根目录，默认当前目录")
    parser.add_argument("--list-devices", action="store_true", help="仅查询账号设备列表")
    args = parser.parse_args(argv)
    for variable in ("MI_USER", "MI_PASS", *(() if args.list_devices else ("MI_DID",))):
        if not _configured(os.environ.get(variable)):
            print(f"请先在当前终端设置 {variable}；凭据和设备标识仅保留本机。", file=sys.stderr)
            return 2
    upstream = args.upstream.resolve()
    if not (upstream / "main.py").is_file() or not (upstream / "src/xiaomi/miservice/__init__.py").is_file():
        print("请使用 --upstream 指定已准备好的 XiaoAiAgent 仓库根目录。", file=sys.stderr)
        return 2
    try:
        backend = importlib.import_module("miservice")
        if getattr(backend, "__version__", None) != "3.0.2":
            raise ImportError("incompatible optional backend")
    except ImportError:
        print("请在 XiaoAiAgent 虚拟环境中安装 config/requirements-xiaoaiagent-otp.txt 固定的可选依赖。", file=sys.stderr)
        return 2

    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
    previous_cwd, previous_path, previous_argv = Path.cwd(), sys.path[:], sys.argv
    failures: list[LoginNotComplete] = []
    try:
        sys.path.insert(0, str(upstream))
        os.chdir(upstream)
        native = importlib.import_module("src.xiaomi.miservice")
        original_account = native.MiAccount
        try:
            native.MiAccount = build_account_class(backend.MiAccount, on_failure=failures.append)
            if args.list_devices:
                try:
                    return asyncio.run(_list_devices(native))
                except LoginNotComplete as error:
                    print(str(error), file=sys.stderr)
                    return 1
                except Exception:
                    print("设备列表查询未完成；网络或服务响应不符合预期，请稍后检查。", file=sys.stderr)
                    return 1
            entrypoint = importlib.import_module("main")
            if entrypoint.get_config().xiaomi.did != os.environ["MI_DID"]:
                print('配置的设备与 MI_DID 不一致；请将 config.yaml 的 xiaomi.did 设为 "${MI_DID}"。', file=sys.stderr)
                return 2
            sys.argv = [str(upstream / "main.py")]
            original_speaker = entrypoint.XiaoAiSpeakerClient
            try:
                entrypoint.XiaoAiSpeakerClient = build_speaker_class(original_speaker)
                entrypoint.main()
                return 1 if failures else 0
            finally:
                entrypoint.XiaoAiSpeakerClient = original_speaker
        finally:
            native.MiAccount = original_account
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path
        sys.argv = previous_argv
