"""Frozen sidecar must stay free of tkinter / customtkinter."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"


def _run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), str(SRC), env.get("PYTHONPATH", "")]
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


_ASSERT_NO_UI = (
    "ui = [m for m in sys.modules if m == 'tkinter' or m.startswith('tkinter.') "
    "or m == 'customtkinter' or m.startswith('customtkinter.')]; "
    "raise SystemExit(0 if not ui else 'ui loaded: ' + repr(ui))"
)


def test_sidecar_server_import_does_not_load_ui() -> None:
    proc = _run_isolated(
        "import sys; from sidecar.server import create_server; " + _ASSERT_NO_UI
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
