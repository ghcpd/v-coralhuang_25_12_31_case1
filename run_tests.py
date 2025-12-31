#!/usr/bin/env python3
"""
Run Tests Script for MiniApp Route Manifest Feature

This script installs pytest if needed, runs the full test suite,
and provides a detailed summary including pass/fail breakdown,
execution time, and coverage percentage.
"""

import subprocess
import sys
import time
import os

def install_pytest():
    """Install pytest if not available"""
    try:
        import pytest
        print("pytest is already installed.")
    except ImportError:
        print("Installing pytest...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
        try:
            import pytest
            print("pytest installed successfully.")
        except ImportError:
            print("Failed to install pytest. Please install it manually.")
            sys.exit(1)

def install_coverage():
    """Install pytest-cov for coverage if possible"""
    try:
        import pytest_cov
        print("pytest-cov is already installed.")
        return True
    except ImportError:
        try:
            print("Installing pytest-cov for coverage...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest-cov"])
            import pytest_cov
            print("pytest-cov installed successfully.")
            return True
        except (ImportError, subprocess.CalledProcessError):
            print("pytest-cov not available, running without coverage.")
            return False

def run_tests():
    """Run the test suite"""
    start_time = time.time()
    
    # Check if test_routes.py exists
    if not os.path.exists("test_routes.py"):
        print("Error: test_routes.py not found.")
        sys.exit(1)
    
    # Try to run with coverage
    has_cov = install_coverage()
    
    cmd = [sys.executable, "-m", "pytest", "test_routes.py", "--tb=short", "--quiet"]
    if has_cov:
        cmd.extend(["--cov=miniapp", "--cov-report=term-missing"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Parse results
    output = result.stdout + result.stderr
    print(output)
    
    # Extract summary from output
    lines = output.split('\n')
    summary_line = None
    for line in reversed(lines):
        if 'passed' in line and 'failed' in line:
            summary_line = line
            break
    
    if summary_line:
        print(f"\nTest Summary: {summary_line}")
    else:
        print("\nCould not parse test summary.")
    
    print(".2f")
    
    # Check for coverage
    if has_cov and "TOTAL" in output:
        # Extract coverage percentage
        for line in reversed(lines):
            if "TOTAL" in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        coverage = float(parts[-1].rstrip('%'))
                        print(".1f")
                    except ValueError:
                        pass
                break
    
    # Exit with appropriate code
    if result.returncode != 0:
        print("Tests failed!")
        sys.exit(1)
    else:
        print("All tests passed!")

if __name__ == "__main__":
    install_pytest()
    run_tests()