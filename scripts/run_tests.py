#!/usr/bin/env python3
"""Run the one fixed automated skill gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 1:
        print("run_tests.py accepts no arguments.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped or result.expectedFailures or result.unexpectedSuccesses:
        print("Skipped or expected-failure tests are forbidden.", file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
