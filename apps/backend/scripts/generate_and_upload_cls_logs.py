"""Run the explicit Tencent Cloud CLS fixture uploader."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root / "src"))
    runpy.run_module("super_ai.cli.cls_logs", run_name="__main__")
