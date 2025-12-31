#!/usr/bin/env python3
"""Run tests (installs pytest if necessary) and print a concise summary.

Usage: python run_tests.py
"""
import sys
import time
import subprocess
import json

try:
    import pytest
except Exception:
    print("pytest not found — installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"], stdout=subprocess.DEVNULL)
    import pytest

start = time.time()
ret = pytest.main(["-q"])  # -q for concise output
end = time.time()

total_time = end - start

# Gather results from pytest (pytest.main return code semantics)
if ret == 0:
    print("\n✅ All tests passed")
else:
    print("\n❌ Some tests failed (exit code: {} )".format(ret))

print(f"Test execution time: {total_time:.3f}s")
# exit with same code as pytest
sys.exit(ret)
