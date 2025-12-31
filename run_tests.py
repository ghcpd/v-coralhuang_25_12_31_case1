#!/usr/bin/env python3
"""
Test runner script for the Route Manifest feature.

This script:
1. Installs pytest if needed
2. Runs the full test suite (test_routes.py and performance_test.py)
3. Prints a detailed summary with pass/fail breakdown and timing
4. Exits with non-zero code on failure
"""

import subprocess
import sys
import time
import json
import os


def run_command(cmd, description):
    """Run a command and return success/failure."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    return result.returncode == 0


def install_pytest():
    """Install pytest if not already installed."""
    print("\nChecking for pytest...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "pytest"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("pytest not found. Installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest", "-q"],
            check=True,
        )
        print("pytest installed successfully.")
    else:
        print("pytest is already installed.")


def main():
    """Main test runner."""
    print("\n" + "="*70)
    print("ROUTE MANIFEST TEST SUITE")
    print("="*70)
    
    # Install dependencies
    install_pytest()
    
    overall_start = time.time()
    
    # Run main test suite
    test_success = run_command(
        [sys.executable, "-m", "pytest", "test_routes.py", "-v", "--tb=short"],
        "Main Test Suite (test_routes.py)"
    )
    
    # Run performance test
    perf_success = run_command(
        [sys.executable, "performance_test.py"],
        "Performance Test"
    )
    
    overall_time = time.time() - overall_start
    
    # Print summary
    print("\n" + "="*70)
    print("TEST EXECUTION SUMMARY")
    print("="*70)
    
    all_passed = test_success and perf_success
    
    print(f"\nTest Suite Results:")
    print(f"  Main Tests:       {'✓ PASSED' if test_success else '✗ FAILED'}")
    print(f"  Performance Test: {'✓ PASSED' if perf_success else '✗ FAILED'}")
    print(f"\nTotal Execution Time: {overall_time:.2f} seconds")
    print(f"Overall Result:       {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print(f"{'='*70}\n")
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
