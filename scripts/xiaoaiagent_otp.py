"""Run with the prepared XiaoAiAgent Python interpreter, from its root folder."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xiaoai_lab.upstream_auth import main


if __name__ == "__main__":
    raise SystemExit(main())
