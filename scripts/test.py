#!/usr/bin/env python3
"""Run every repo check. This is what CI runs.

Steps (all run, even after a failure, then a summary):

1. ``scripts/sync.py --check`` - ground-rules blocks and the agent-plugin/skills mirror
2. ``scripts/validate.py``      - every repo invariant
3. ``python -m unittest discover -s tests`` - unit tests (the mock-server tests
   skip themselves when the ``mcp`` package is not installed)

Usage::

    python3 scripts/test.py            # everything
    python3 scripts/test.py -v         # verbose unit tests

Exit code 0 only when every step passes. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent


def run_step(label: str, cmd: List[str]) -> Tuple[str, int, float]:
    print(f"\n=== {label}: {' '.join(cmd)}", flush=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    code = subprocess.call(cmd, cwd=str(ROOT), env=env)
    return label, code, time.monotonic() - started


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run sync --check, validate and the unit tests.")
    ap.add_argument("-v", "--verbose", action="store_true", help="verbose unit test output")
    args = ap.parse_args(argv)

    py = sys.executable
    steps = [
        ("sync --check", [py, "scripts/sync.py", "--check"]),
        ("validate", [py, "scripts/validate.py"]),
        ("unit tests", [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"] + (["-v"] if args.verbose else [])),
    ]
    results = [run_step(label, cmd) for label, cmd in steps]

    print("\n=== summary")
    for label, code, secs in results:
        print(f"  {'PASS' if code == 0 else 'FAIL'}  {label}  ({secs:.1f}s)")
    failed = [label for label, code, _ in results if code != 0]
    if failed:
        print(f"test.py: {len(failed)} step(s) failed: {', '.join(failed)}")
        return 1
    print("test.py: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
