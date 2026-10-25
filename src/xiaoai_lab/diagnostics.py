"""Read-only environment and network checks. No device credentials or writes."""

from __future__ import annotations

import ipaddress
import json
import platform
import socket
import sys
import urllib.error
import urllib.request
from typing import Any

RFC1918 = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)
DEFAULT_PORTS = (22, 23, 80, 443, 8080, 8443)


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
    results = []
    for port in ports:
        if not 1 <= port <= 65535:
            raise ValueError("端口范围必须在 1..65535")
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                status = "open"
        except (TimeoutError, OSError):
            status = "not_open_or_filtered"
        results.append({"port": port, "status": status})
    return {"target": ip, "mode": "tcp_connect_read_only", "results": results}


def check_ollama(url: str = "http://127.0.0.1:11434", timeout: float = 1.5) -> dict[str, Any]:
    endpoint = url.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(endpoint, timeout=timeout) as response:
            payload = json.load(response)
        names = [x.get("name", "") for x in payload.get("models", []) if isinstance(x, dict)]
        return {"status": "ok", "models": names}
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        return {"status": "unavailable", "models": []}


def doctor(ollama_url: str = "http://127.0.0.1:11434") -> dict[str, Any]:
    return {
        "project": "XiaoAi-Lab",
        "phase": "M0 local diagnostics",
        "python": sys.version.split()[0],
        "system": platform.system(),
        "machine": platform.machine(),
        "ollama": check_ollama(ollama_url),
        "device_tested": False,
    }
