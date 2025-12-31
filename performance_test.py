#!/usr/bin/env python3
"""
Performance Test for Route Manifest Generation

This script registers 1000+ routes and measures the time taken
to generate the route manifest, verifying the performance target
of < 1 second for 1000 routes.
"""

import time
from miniapp import MiniApp, Blueprint

def create_performance_test_app():
    """Create an app with 1000+ routes for performance testing"""
    app = MiniApp("performance_test")
    
    # Create multiple blueprints
    admin_bp = Blueprint("admin")
    api_bp = Blueprint("api")
    user_bp = Blueprint("user")
    
    # Register static routes
    for i in range(100):
        app.route(f"/static/{i}", method="GET", source="static.py", endpoint=f"static_{i}")(lambda: "static")
    
    # Register dynamic routes with varying complexity
    for i in range(200):
        app.route(f"/users/<user_id>/posts/{i}", method="GET", source="users.py", endpoint=f"user_posts_{i}")(lambda: "posts")
    
    # Register complex routes
    for i in range(100):
        app.route(f"/api/<version>/users/<user_id>/posts/<post_id>/comments/{i}", method="GET", source="api.py", endpoint=f"complex_{i}")(lambda: "complex")
    
    # Register routes with :param syntax
    for i in range(100):
        app.route(f"/data/:category/items/:item_id/details/{i}", method="GET", source="data.py", endpoint=f"data_{i}")(lambda: "data")
    
    # Register blueprint routes
    for i in range(50):
        admin_bp.route(f"/stats/{i}", method="GET", source="admin.py", endpoint=f"admin_stats_{i}")(lambda: "admin")
    
    for i in range(100):
        api_bp.route(f"/v1/resources/{i}", method="GET", source="api.py", endpoint=f"api_resource_{i}")(lambda: "api")
    
    for i in range(50):
        user_bp.route(f"/profile/<user_id>/settings/{i}", method="GET", source="user.py", endpoint=f"user_setting_{i}")(lambda: "user")
    
    # Register blueprints
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/user")
    
    # Add some conflicts for testing
    app.route("/conflict", method="GET", source="conflict.py", endpoint="conflict1")(lambda: "conflict")
    app.route("/conflict", method="GET", source="conflict.py", endpoint="conflict2")(lambda: "conflict")
    
    # Add similar paths
    app.route("/api/user/profile", method="GET", source="similar.py", endpoint="user_profile")(lambda: "profile")
    app.route("/api/users/profile", method="GET", source="similar.py", endpoint="users_profile")(lambda: "profiles")
    
    return app

def run_performance_test():
    """Run the performance test"""
    print("Creating performance test app with 1000+ routes...")
    app = create_performance_test_app()
    
    print("Generating route manifest...")
    start_time = time.time()
    manifest = app.route_manifest()
    end_time = time.time()
    
    execution_time = end_time - start_time
    total_routes = manifest["summary"]["total_routes"]
    
    print(f"Manifest generated in {execution_time:.4f} seconds")
    print(f"Total routes: {total_routes}")
    print(f"Conflicts detected: {manifest['summary']['total_conflicts']}")
    print(f"Warnings detected: {manifest['summary']['total_warnings']}")
    
    # Performance check
    if execution_time < 1.0:
        print("✓ Performance target met: < 1 second for 1000+ routes")
    else:
        print(f"✗ Performance target not met: {execution_time:.4f} seconds (should be < 1.0)")
    
    # Print some stats
    print(f"Average complexity: {sum(r['complexity_score'] for r in manifest['routes']) / total_routes:.2f}")
    print(f"Dynamic routes: {manifest['pattern_analysis']['total_dynamic_routes']}")
    
    return execution_time < 1.0

if __name__ == "__main__":
    success = run_performance_test()
    exit(0 if success else 1)