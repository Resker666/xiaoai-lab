"""Command-line utilities for the M0 speaker baseline."""

from __future__ import annotations

import argparse
import json
import sys

from .diagnostics import DEFAULT_PORTS, doctor, probe_tcp
from .reports import write_report


def _parse_ports(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(port.strip()) for port in value.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("端口须为逗号分隔的整数，例如 22,80,443") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xiaoai-lab",
        description="L05C 安全实验工具：只读环境检查和指定设备 TCP 探测",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    environment = commands.add_parser("doctor", help="检查 Python 与本机 Ollama 环境")
    environment.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    environment.add_argument("--timeout", type=float, default=1.5, help="HTTP socket 超时秒数，0 < 值 <= 10（默认 1.5）")
    network = commands.add_parser("probe", help="只读 TCP connect 探测自有设备的局域网 IP")
    network.add_argument("--ip", required=True, help="音箱的 IPv4 地址，例如 192.168.1.105")
    network.add_argument("--ports", type=_parse_ports, default=DEFAULT_PORTS, help="逗号分隔的 TCP 端口，最多 32 个（默认 22,23,80,443,8080,8443）")
    network.add_argument("--timeout", type=float, default=0.6, help="每个 TCP 连接的超时秒数，0 < 值 <= 10（默认 0.6）")
    for command in (environment, network):
        command.add_argument("--output", help="另存私有 UTF-8 JSON 报告；建议 reports/ 下的新文件，不覆盖已有文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Redirected streams on English Windows may otherwise use CP1252, which
    # cannot encode Chinese help/errors or valid Unicode model names.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        data = (
            doctor(args.ollama_url, args.timeout)
            if args.command == "doctor"
            else probe_tcp(args.ip, args.ports, args.timeout)
        )
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2
    if args.output:
        try:
            write_report(args.output, data)
        except FileExistsError:
            print("报告未保存：文件已存在，请使用新的文件名。", file=sys.stderr)
            return 1
        except (OSError, ValueError):
            print("报告未保存：请检查输出路径、磁盘空间和写入权限。", file=sys.stderr)
            return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0
