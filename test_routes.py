from miniapp import MiniApp, Blueprint


def test_manifest_contains_routes():
    app = MiniApp()

    @app.route("/health", method="GET", source="app.py")
    def health():
        return "ok"

    manifest = app.route_manifest()
    assert "routes" in manifest
    paths = [r["path"] for r in manifest["routes"]]
    assert "/health" in paths


def test_manifest_contains_blueprint_routes_with_prefix():
    app = MiniApp()
    bp = Blueprint("admin")

    @bp.route("/stats", method="GET", source="admin.py")
    def stats():
        return "stats"

    app.register_blueprint(bp, url_prefix="/admin")

    manifest = app.route_manifest()
    paths = [r["path"] for r in manifest["routes"]]
    assert "/admin/stats" in paths

    entry = next(r for r in manifest["routes"] if r["path"] == "/admin/stats")
    assert entry.get("blueprint") == "admin"


def test_detects_route_conflict_same_method_and_path():
    app = MiniApp()

    @app.route("/items", method="GET", source="a.py")
    def items_a():
        return 1

    @app.route("/items", method="GET", source="b.py")
    def items_b():
        return 2

    manifest = app.route_manifest()
    assert "conflicts" in manifest

    # 至少要能报告该冲突
    assert any(c["method"] == "GET" and c["path"] == "/items" for c in manifest["conflicts"])


def test_manifest_is_json_serializable():
    import json
    app = MiniApp()

    @app.route("/x", method="GET")
    def x():
        return "x"

    m = app.route_manifest()
    json.dumps(m)  # should not raise
