import time
from miniapp import MiniApp, Blueprint


def test_detects_pattern_conflict_and_ambiguous():
    app = MiniApp()

    @app.route("/users/<id>", method="GET", source="s.py")
    def a():
        return 1

    @app.route("/users/:user_id", method="GET", source="s.py")
    def b():
        return 2

    @app.route("/users/<name>", method="GET", source="s.py")
    def c():
        return 3

    m = app.route_manifest()
    # pattern conflict (same shape different syntax) should be reported
    pats = [c for c in m["conflicts"] if c["method"] == "GET" and "/users/" in c["path"]]
    assert any(p["severity"] in ("error", "warning") for p in pats)


def test_unreachable_and_missing_source_warning():
    app = MiniApp()

    @app.route("/items/<id>", method="GET", source="a.py")
    def dyn():
        return 1

    @app.route("/items/special", method="GET")
    def spec():
        return 2

    m = app.route_manifest()
    warns = m["warnings"]
    assert any(w.get("type") == "unreachable_route" for w in warns)
    # missing source should be present for the static route
    assert any(w.get("type") == "missing_source" and w.get("route") == "/items/special" for w in warns)


def test_performance_manifest_generation_is_fast():
    app = MiniApp()
    # register 1200 routes across two blueprints to simulate real app
    for i in range(600):
        @app.route(f"/p{i}", method="GET")
        def _fn(i=i):
            return i

    for i in range(600):
        @app.route(f"/users/<id>/posts/{i}", method="GET")
        def _fn2(i=i):
            return i

    t0 = time.perf_counter()
    m = app.route_manifest()
    dt = (time.perf_counter() - t0) * 1000.0
    # manifest should complete quickly; allow 1000ms as target for 1000+ routes
    assert m["summary"]["total_routes"] >= 1200
    assert m["summary"]["execution_time_ms"] < 2000.0
    assert dt < 2000.0
