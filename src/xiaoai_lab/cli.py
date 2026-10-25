"""Command-line utilities for the M0 speaker baseline."""

from __future__ import annotations

import argparse
import json

from .diagnostics import doctor, probe_tcp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xiaoai-lab",
        description="L05C 安全实验工具：只读环境检查和指定设备 TCP 探测",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    environment = commands.add_parser("doctor", help="检查 Python 与本机 Ollama 环境")
    environment.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    network = commands.add_parser("probe", help="只读 TCP connect 探测自有设备的局域网 IP")
    network.add_argument("--ip", required=True, help="音箱的 IPv4 地址，例如 192.168.1.105")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = doctor(args.ollama_url) if args.command == "doctor" else probe_tcp(args.ip)
    except ValueError as exc:
        print(f"参数错误：{exc}")
        return 2
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0
