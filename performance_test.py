"""Quick performance measurement for route_manifest().

Run: python performance_test.py
"""
from miniapp import MiniApp
import time


def build_app(n=1000):
    app = MiniApp()
    for i in range(n // 2):
        @app.route(f"/static/item_{i}", method="GET")
        def _s(i=i):
            return i
    for i in range(n // 2):
        @app.route(f"/users/:user_id/profile/{i}", method="GET")
        def _d(i=i):
            return i
    return app


def run(n=1000):
    app = build_app(n)
    t0 = time.perf_counter()
    m = app.route_manifest()
    dt = (time.perf_counter() - t0) * 1000.0
    print(f"Registered routes: {m['summary']['total_routes']}")
    print(f"Manifest generation time: {m['summary']['execution_time_ms']} ms (measured {dt:.2f} ms)")
    return dt, m


if __name__ == '__main__':
    run(1200)
