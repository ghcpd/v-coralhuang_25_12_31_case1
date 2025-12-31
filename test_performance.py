import time
from performance_test import run


def test_manifest_performance_1000_routes():
    """Ensure manifest generation completes under 1 second for 1000 routes."""
    elapsed_ms = run(1000)
    assert elapsed_ms < 1000.0
