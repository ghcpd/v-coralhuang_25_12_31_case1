import time
import json
from miniapp import MiniApp


def performance_run(total_routes: int = 1000):
    app = MiniApp()

    # Register a mix of static and dynamic routes to emulate realistic workload
    for i in range(total_routes // 3):
        @app.route(f"/items/{i}", method="GET")
        def _static(i=i):
            return str(i)

    for i in range(total_routes // 3, 2 * total_routes // 3):
        @app.route(f"/products/<id>/detail/{i}", method="GET")
        def _prod(id, i=i):
            return str(i)

    for i in range(2 * total_routes // 3, total_routes):
        @app.route(f"/users/:user_id/profile/{i}", method="GET")
        def _user(user_id, i=i):
            return str(i)

    t0 = time.perf_counter()
    manifest = app.route_manifest()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    print(f"manifest_time_ms: {elapsed_ms:.2f}")

    # Write a sample manifest
    with open('sample_manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Basic assertion for performance target
    if elapsed_ms > 1000.0:
        print(f"WARNING: manifest generation exceeded 1000ms: {elapsed_ms:.2f}ms")
        return 1
    print("Performance target met: <1000ms")
    return 0


if __name__ == '__main__':
    import sys
    total = 1200
    if len(sys.argv) > 1:
        try:
            total = int(sys.argv[1])
        except Exception:
            pass
    rc = performance_run(total)
    raise SystemExit(rc)
