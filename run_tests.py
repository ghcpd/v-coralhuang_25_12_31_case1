#!/usr/bin/env python
"""Run tests, performance checks, and produce a short summary.
"""
import subprocess
import sys
import re
import time
import shlex

PY = sys.executable

def pip_install(packages):
    cmd = [PY, '-m', 'pip', 'install', '--quiet'] + packages
    return subprocess.call(cmd) == 0


def run_cmd(cmd):
    # Prefer list-args to ensure cross-platform behavior on Windows
    try:
        if isinstance(cmd, str):
            parts = cmd.split()
        else:
            parts = cmd
        proc = subprocess.Popen(parts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, text=True)
        out, _ = proc.communicate()
        return proc.returncode, out
    except Exception as exc:
        return 1, str(exc)


def main():
    start = time.perf_counter()
    print('Installing test dependencies (pytest, pytest-cov)')
    pip_install(['pytest', 'pytest-cov'])

    print('Running pytest...')
    rc, out = run_cmd([PY, '-m', 'pytest', '-q'])
    print(out)

    # Parse pytest summary
    total_tests = None
    passed = None
    failed = None
    time_taken = None
    m = re.search(r"=+ (\d+) passed", out)
    if m:
        passed = int(m.group(1))
    m2 = re.search(r"=+ (\d+) failed", out)
    if m2:
        failed = int(m2.group(1))
    m3 = re.search(r"in ([0-9\.]+)s", out)
    if m3:
        time_taken = float(m3.group(1))

    # Coverage
    print('Running pytest with coverage...')
    rc_cov, out_cov = run_cmd([PY, '-m', 'pytest', '--maxfail=1', '--disable-warnings', '-q', '--cov=.'])
    print(out_cov)
    cov_percent = None
    m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", out_cov)
    if m:
        cov_percent = int(m.group(1))

    # Run performance test
    print('Running performance_test.py...')
    rc_perf, out_perf = run_cmd([PY, 'performance_test.py'])
    print(out_perf)
    perf_time_ms = None
    m = re.search(r"manifest_time_ms: ([0-9\.]+)", out_perf)
    if m:
        perf_time_ms = float(m.group(1))

    overall_time = (time.perf_counter() - start)

    print('\n=== Test Summary ===')
    if passed is not None:
        print(f'Passed: {passed}')
    if failed is not None:
        print(f'Failed: {failed}')
    if time_taken is not None:
        print(f'Test execution time (pytest): {time_taken:.2f}s')
    if cov_percent is not None:
        print(f'Coverage: {cov_percent}%')
    if perf_time_ms is not None:
        print(f'Performance manifest_time_ms: {perf_time_ms:.2f}ms')
    print(f'Overall run time: {overall_time:.2f}s')

    # Exit non-zero if any step failed
    if rc != 0 or rc_cov != 0 or rc_perf != 0:
        print('One or more steps failed')
        raise SystemExit(1)
    print('All steps completed successfully')

if __name__ == '__main__':
    main()
