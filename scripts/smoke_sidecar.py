#!/usr/bin/env python3
"""Smoke frozen argos_sidecar.exe: spawn, /health, optional /v1/translate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
TOKEN = "smoke-sidecar-token"


def _find_exe(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        raise SystemExit(f"sidecar exe not found: {path}")
    candidates = [
        ROOT / "dist" / "ArgosTranslate" / "sidecar" / "argos_sidecar.exe",
        ROOT / "dist" / "argos_sidecar" / "argos_sidecar.exe",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise SystemExit("argos_sidecar.exe not found; pass --exe")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke frozen sidecar")
    parser.add_argument("--exe", default="", help="Path to argos_sidecar.exe")
    args = parser.parse_args(argv)
    exe = _find_exe(args.exe or None)
    env = os.environ.copy()
    env["ARGOS_SIDECAR_TOKEN"] = TOKEN
    proc = subprocess.Popen(
        [str(exe), "--host", "127.0.0.1", "--port", "0"],
        cwd=str(exe.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    port = 0
    deadline = time.time() + 45
    try:
        while time.time() < deadline:
            ready = Path(os.environ.get("TEMP", os.environ.get("TMP", "."))) / (
                f"argos-sidecar-ready-{proc.pid}.json"
            )
            if ready.exists():
                payload = json.loads(ready.read_text(encoding="utf-8"))
                if payload.get("ok") and payload.get("port"):
                    port = int(payload["port"])
                    break
            if proc.poll() is not None:
                err = proc.stderr.read() if proc.stderr else ""
                print(f"sidecar exited {proc.returncode}: {err}", file=sys.stderr)
                return 1
            time.sleep(0.2)
        if not port:
            print("sidecar ready handshake timed out", file=sys.stderr)
            return 1
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(timeout=10) as client:
            health = client.get(f"{base}/health")
            health.raise_for_status()
            body = health.json()
            if body.get("ok") is not True:
                print(f"/health not ok: {body}", file=sys.stderr)
                return 1
            auth = client.get(
                f"{base}/v1/health",
                headers={"X-Sidecar-Token": TOKEN},
            )
            auth.raise_for_status()
        print(f"sidecar smoke OK port={port} version={body.get('version')}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
