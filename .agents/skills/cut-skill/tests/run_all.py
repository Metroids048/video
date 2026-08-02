"""Unified test runner: runs every suite and prints a compact summary."""
import os
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TESTS_DIR = Path(__file__).parent
TESTS = [
    ("test_draft.py", "Draft parsing and basic operations"),
    ("test_e2e.py", "End-to-end workflow"),
    ("test_mcp.py", "MCP dispatch_tool"),
    ("test_cli.py", "CLI commands"),
    ("test_http.py", "HTTP API"),
    ("test_regression.py", "Bug fix regression tests"),
    ("test_pro.py", "Professional editing features"),
    ("test_agent_compat.py", "Agent compatibility and skill metadata"),
    ("test_professional_workflow.py", "Director planning and export QA"),
]


def run_one(test_file: str, desc: str):
    print(f"\n{'=' * 60}")
    print(f"Running: {test_file} - {desc}")
    print(f"{'=' * 60}")
    start = time.time()
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, str(TESTS_DIR / test_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(TESTS_DIR),
        env=env,
    )
    elapsed = time.time() - start
    out_lines = r.stdout.strip().split("\n")
    err_lines = r.stderr.strip().split("\n")
    if r.stdout:
        print("\n".join(out_lines[-15:]))
    if r.returncode != 0 and r.stderr:
        print("\n--- stderr ---")
        print("\n".join(err_lines[-20:]))
    status = "PASS" if r.returncode == 0 else "FAIL"
    print(f"\n[{status}] {test_file} ({elapsed:.1f}s)")
    return r.returncode == 0


def main():
    print("cut.skill test suite")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Tests dir: {TESTS_DIR}")

    results = []
    for tf, desc in TESTS:
        ok = run_one(tf, desc)
        results.append((tf, desc, ok))

    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    passed = sum(1 for _, _, ok in results if ok)
    total = len(results)
    for tf, desc, ok in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  {mark:4s} {tf:30s} {desc}")
    print(f"\n  {passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
