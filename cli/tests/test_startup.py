"""Startup time test — `ocmo --help` must complete in under 200 ms."""

import subprocess
import sys
import time


def test_help_under_200ms() -> None:
    """ocmo --help must return within 200 ms (warm cache)."""
    # Warm up
    subprocess.run(
        [sys.executable, "-m", "ocmo_cli", "--help"],
        capture_output=True,
        timeout=5,
    )

    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "ocmo_cli", "--help"],
        capture_output=True,
        timeout=5,
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    assert result.returncode == 0, f"--help failed: {result.stderr.decode()}"
    assert elapsed_ms < 200, f"--help took {elapsed_ms:.0f} ms, exceeds 200 ms budget"
