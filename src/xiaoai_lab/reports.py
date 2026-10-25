"""Private JSON report persistence; no redaction or device verification implied."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_report(path: str | Path, data: dict[str, Any]) -> None:
    """Write a new UTF-8 record, refusing to replace an earlier experiment."""
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as output:
        output.write(text)
