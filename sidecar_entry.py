"""PyInstaller entry: frozen HTTP sidecar without CustomTkinter GUI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sidecar.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
