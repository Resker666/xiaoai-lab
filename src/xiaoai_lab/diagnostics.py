"""Read-only environment and network checks. No device credentials or writes."""

from __future__ import annotations

import ipaddress
import errno
import json
import math
import platform
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.client import HTTPException
from typing import Any

from . import __version__

RFC1918 = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)
DEFAULT_PORTS = (22, 23, 80, 443, 8080, 8443)
MAX_PORTS = 32
MAX_RESPONSE_BYTES = 1024 * 1024


def report_metadata() -> dict[str, Any]:
    """Version reports without implying physical-device verification."""
    return {
        "schema_version": 1,
        "tool_version": __version__,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "device_tested": False,
    }


def validate_timeout(timeout: float) -> float:
    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 10:
        raise ValueError("超时必须为大于 0 且不超过 10 秒的有限数值")
    return timeout


def validate_lan_ipv4(value: str) -> str:
    """Only permit numeric private RFC1918 addresses; reject domains and public IPs."""
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError("请输入 RFC1918 局域网 IPv4 地址，例如 192.168.1.105") from exc
    if not any(address in subnet for subnet in RFC1918):
        raise ValueError("仅允许对拥有或授权的 RFC1918 私有 IPv4 地址探测")
    if str(address).endswith((".0", ".255")):
        # Safe conservative rule for typical home /24 networks; may exclude unusual subnet hosts.
        raise ValueError("不接受疑似网段/广播地址，请确认具体设备 IP")
    return str(address)


def probe_tcp(ip: str, ports: tuple[int, ...] = DEFAULT_PORTS, timeout: float = 0.6) -> dict[str, Any]:
    ip = validate_lan_ipv4(ip)
    timeout = validate_timeout(timeout)
    if not ports or any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        raise ValueError("端口必须是 1..65535 范围内的整数，且列表不能为空")
    ports = tuple(dict.fromkeys(ports))
    if len(ports) > MAX_PORTS:
        raise ValueError(f"每次最多探测 {MAX_PORTS} 个不同端口")
    report = report_metadata()
    results = []
    for port in ports:
        started = time.monotonic()
        error_code = None
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                status = "open"
        except OSError as exc:
            error_code = getattr(exc, "winerror", None) or exc.errno
            if isinstance(exc, TimeoutError) or error_code in (errno.ETIMEDOUT, 10060):
                status = "timeout"
            elif isinstance(exc, ConnectionRefusedError) or error_code in (errno.ECONNREFUSED, 10061):
                status = "closed"
            elif error_code in (errno.EHOSTUNREACH, errno.ENETUNREACH, 10051, 10065):
                status = "unreachable"
            elif error_code in (errno.EACCES, errno.EPERM, 10013):
                status = "permission_denied"
            else:
                status = "error"
        result = {"port": port, "status": status, "elapsed_ms": round((time.monotonic() - started) * 1000, 3)}
        if error_code is not None:
            result["error_code"] = error_code
        results.append(result)
    return {
        **report,
        "target": ip,
        "mode": "tcp_connect_read_only",
        "timeout_seconds": timeout,
        "results": results,
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _tags_endpoint(url: str) -> str:
    message = "Ollama 地址必须为无账号、查询参数或片段的 HTTP(S) 基础 URL"
    if any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise ValueError(message)
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
        valid = (
            parsed.scheme in ("http", "https") and parsed.hostname
            and not parsed.username and not parsed.password
            and "@" not in parsed.netloc and not parsed.query and not parsed.fragment
            and (port is None or 1 <= port <= 65535)
        )
    except ValueError:
        raise ValueError(message) from None
    if not valid:
        raise ValueError(message)
    return url.rstrip("/") + "/api/tags"


def check_ollama(url: str = "http://127.0.0.1:11434", timeout: float = 1.5) -> dict[str, Any]:
    endpoint = _tags_endpoint(url)
    timeout = validate_timeout(timeout)
    # Explicit endpoint only: don't forward local checks to a system proxy or redirect.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(endpoint, timeout=timeout) as response:
            if response.status != 200:
                return {"status": "unavailable", "models": [], "reason": "http_error", "http_status": response.status}
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            return {"status": "invalid_response", "models": [], "reason": "response_too_large"}
        payload = json.loads(body)
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            return {"status": "invalid_response", "models": [], "reason": "invalid_schema"}
        models = payload["models"]
        if any(not isinstance(model, dict) or not isinstance(model.get("name"), str) or not model["name"].strip() for model in models):
            return {"status": "invalid_response", "models": [], "reason": "invalid_schema"}
        names = [model["name"] for model in models]
        try:
            for name in names:
                name.encode("utf-8")
        except UnicodeEncodeError:
            return {"status": "invalid_response", "models": [], "reason": "invalid_schema"}
        return {"status": "ok", "models": names}
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        return {"status": "unavailable", "models": [], "reason": "http_error", "http_status": code}
    except (ValueError, UnicodeError, RecursionError):
        return {"status": "invalid_response", "models": [], "reason": "invalid_json"}
    except (OSError, urllib.error.URLError, HTTPException):
        return {"status": "unavailable", "models": [], "reason": "connection_error"}


def doctor(ollama_url: str = "http://127.0.0.1:11434", timeout: float = 1.5) -> dict[str, Any]:
    return {
        **report_metadata(),
        "project": "XiaoAi-Lab",
        "phase": "M0 local diagnostics",
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 10),
        "system": platform.system(),
        "machine": platform.machine(),
        "ollama": check_ollama(ollama_url, timeout),
    }
