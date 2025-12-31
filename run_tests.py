#!/usr/bin/env python3
"""Run the test suite (installs pytest/pytest-cov if needed) and print a detailed summary.

Usage: python run_tests.py
"""
import json
import shutil
import subprocess
import sys
import time

REQ = ["pytest", "pytest-cov"]
start = time.perf_counter()
# ensure pip
py = sys.executable
try:
    import pytest  # type: ignore
except Exception:
    subprocess.check_call([py, "-m", "pip", "install"] + REQ)
else:
    # ensure pytest-cov available
    try:
        import pytest_cov  # type: ignore
    except Exception:
        subprocess.check_call([py, "-m", "pip", "install", "pytest-cov"])

cmd = [py, "-m", "pytest", "-q", "--disable-warnings", "--maxfail=1", "--cov=.", "--cov-report=term"]
print("Running tests: ", " ".join(cmd))
proc = subprocess.run(cmd, capture_output=True, text=True)
end = time.perf_counter()
output = proc.stdout + "\n" + proc.stderr
print(output)
# parse summary
passed = failed = skipped = 0
lines = output.splitlines()
for L in lines:
    if L.strip().endswith("passed") and "passed," in L:
        # example: 5 passed, 1 skipped
        parts = [p.strip() for p in L.split(",")]
        for p in parts:
            if p.endswith("passed"):
                passed = int(p.split()[0])
            if p.endswith("failed"):
                failed = int(p.split()[0])
            if p.endswith("skipped"):
                skipped = int(p.split()[0])

# try to find coverage
cov_pct = None
for L in lines:
    if L.strip().startswith("TOTAL") and "%" in L:
        try:
            cov_pct = float(L.strip().split()[-1].strip('%'))
        except Exception:
            pass

summary = {
    "total_tests_run": passed + failed + skipped,
    "passed": passed,
    "failed": failed,
    "skipped": skipped,
    "duration_s": round(end - start, 3),
    "coverage_percent": cov_pct,
}
print("\nTest summary:")
print(json.dumps(summary, indent=2))
if proc.returncode != 0:
    sys.exit(proc.returncode)

print("All tests passed.")
