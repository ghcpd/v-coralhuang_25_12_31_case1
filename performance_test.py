"""Quick performance harness for MiniApp.route_manifest().

Registers 1000 routes and measures manifest generation time.
"""
from miniapp import MiniApp
import time


def run(n: int = 1000) -> float:
    app = MiniApp()

    for i in range(n):
        path = f"/items/{i}/detail/:id_{i}"

        @app.route(path, method="GET", source="performance_test.py")
        def _handler(i=i):
            return i

    start = time.perf_counter()
    m = app.route_manifest()
    end = time.perf_counter()
    elapsed_ms = (end - start) * 1000.0
    print(f"Registered {n} routes — manifest generation: {elapsed_ms:.3f} ms")
    return elapsed_ms


if __name__ == "__main__":
    run(1000)
