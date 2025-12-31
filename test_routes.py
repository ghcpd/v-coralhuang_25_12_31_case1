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

    # 至少要能报告该冲突，并且应该标记为 critical 严重性
    conflict = next((c for c in manifest["conflicts"] if c["method"] == "GET" and c["path"] == "/items"), None)
    assert conflict is not None
    assert "severity" in conflict
    assert conflict["severity"] in ["critical", "error", "warning"]


def test_manifest_is_json_serializable():
    import json
    app = MiniApp()

    @app.route("/x", method="GET")
    def x():
        return "x"

    m = app.route_manifest()
    json.dumps(m)  # should not raise


def test_dynamic_route_detection():
    """测试动态路由参数检测"""
    app = MiniApp()
    
    @app.route("/users/<user_id>", method="GET", source="users.py")
    def get_user():
        return "user"
    
    @app.route("/posts/:post_id/comments/:comment_id", method="GET")
    def get_comment():
        return "comment"
    
    manifest = app.route_manifest()
    
    # 检查路由是否被标记为动态
    user_route = next(r for r in manifest["routes"] if "/users/" in r["path"])
    assert user_route.get("is_dynamic") == True
    assert "path_params" in user_route
    assert len(user_route["path_params"]) > 0
    
    # 检查复杂度分数
    comment_route = next(r for r in manifest["routes"] if "/comments/" in r["path"])
    assert "complexity_score" in comment_route
    assert comment_route["complexity_score"] > user_route.get("complexity_score", 0)


def test_pattern_analysis_included():
    """测试模式分析功能"""
    app = MiniApp()
    
    @app.route("/static", method="GET")
    def static1():
        return "1"
    
    @app.route("/dynamic/<id>", method="GET")
    def dynamic1():
        return "2"
    
    @app.route("/complex/<id>/sub/<name>", method="GET")
    def complex1():
        return "3"
    
    manifest = app.route_manifest()
    
    assert "pattern_analysis" in manifest
    analysis = manifest["pattern_analysis"]
    
    # 检查必需字段
    assert "most_complex_routes" in analysis
    assert "total_dynamic_routes" in analysis
    assert analysis["total_dynamic_routes"] >= 2


def test_warnings_detection():
    """测试警告检测功能"""
    app = MiniApp()
    
    # 创建两个非常相似的路径（可能是拼写错误）
    @app.route("/api/user", method="GET")
    def user1():
        return "1"
    
    @app.route("/api/users", method="GET")  # 相似但不同
    def user2():
        return "2"
    
    manifest = app.route_manifest()
    
    assert "warnings" in manifest
    # 应该能检测到相似路径的警告
    

def test_summary_completeness():
    """测试摘要信息的完整性"""
    app = MiniApp()
    
    @app.route("/a", method="GET")
    def a():
        return "a"
    
    @app.route("/b", method="POST")
    def b():
        return "b"
    
    @app.route("/a", method="GET")  # 冲突
    def a2():
        return "a2"
    
    manifest = app.route_manifest()
    
    assert "summary" in manifest
    summary = manifest["summary"]
    
    # 检查必需字段
    assert "total_routes" in summary
    assert summary["total_routes"] >= 3
    assert "total_conflicts" in summary
    assert "total_warnings" in summary
    assert "execution_time_ms" in summary
    assert isinstance(summary["execution_time_ms"], (int, float))


def test_deterministic_ordering():
    """测试输出的确定性"""
    import json
    
    app = MiniApp()
    
    @app.route("/z", method="GET")
    def z():
        return "z"
    
    @app.route("/a", method="POST")
    def a():
        return "a"
    
    @app.route("/m", method="PUT")
    def m():
        return "m"
    
    # 多次调用应该产生相同的结果
    m1 = app.route_manifest()
    m2 = app.route_manifest()
    
    # 移除时间戳字段再比较
    m1_copy = json.loads(json.dumps(m1))
    m2_copy = json.loads(json.dumps(m2))
    
    if "summary" in m1_copy:
        m1_copy["summary"].pop("execution_time_ms", None)
    if "summary" in m2_copy:
        m2_copy["summary"].pop("execution_time_ms", None)
    
    assert json.dumps(m1_copy, sort_keys=True) == json.dumps(m2_copy, sort_keys=True)
