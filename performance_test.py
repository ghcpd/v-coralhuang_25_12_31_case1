#!/usr/bin/env python3
"""
Performance test for the Route Manifest feature.

This test:
1. Registers 1000+ routes with varying complexity
2. Measures route_manifest() execution time
3. Verifies it completes in < 5 seconds (reasonable for 1200 routes)
4. Generates a performance report
"""

import time
import json
from miniapp import MiniApp, Blueprint


def create_app_with_many_routes(num_routes=1000):
    """Create a test app with many routes."""
    app = MiniApp("perf_test")
    
    # Register various types of routes
    for i in range(num_routes):
        method = ["GET", "POST", "PUT", "DELETE"][i % 4]
        
        # Mix of static and dynamic routes
        if i % 10 == 0:
            # Static routes - make them more unique to avoid typo warnings
            path = f"/static/resource/item_{i:04d}"
            source = f"static_{i}.py"
        elif i % 5 == 0:
            # Single parameter
            path = f"/items/{i}/details"
            source = f"items_{i}.py"
        elif i % 3 == 0:
            # Multiple parameters
            path = f"/users/<user_id>/posts/<post_id>/comments/<comment_id>"
            source = f"comments_{i}.py"
        else:
            # Dynamic with colons
            path = f"/api/:version/resource_{i:04d}/:id/action"
            source = f"api_{i}.py"
        
        # Create handler function
        def make_handler(idx):
            def handler():
                return f"response_{idx}"
            handler.__name__ = f"handler_{idx}"
            return handler
        
        # Register route with endpoint
        app.route(
            path,
            method=method,
            source=source,
            endpoint=f"endpoint_{i}"
        )(make_handler(i))
    
    # Add some blueprint routes
    bp1 = Blueprint("admin")
    bp2 = Blueprint("api")
    
    for i in range(100):
        path = f"/stats_{i}" if i % 2 == 0 else f"/data/<id>"
        bp1.route(path, method="GET", source=f"admin_{i}.py")(
            lambda: "admin"
        )
    
    for i in range(100):
        path = f"/endpoint_{i}" if i % 2 == 0 else f"/resource/<resource_id>"
        bp2.route(path, method="POST", source=f"api_{i}.py")(
            lambda: "api"
        )
    
    app.register_blueprint(bp1, url_prefix="/admin")
    app.register_blueprint(bp2, url_prefix="/v1")
    
    return app


def run_performance_test():
    """Run the performance test."""
    print("\n" + "="*70)
    print("ROUTE MANIFEST PERFORMANCE TEST")
    print("="*70)
    
    print("\n1. Creating test app with 1000+ routes...")
    start_creation = time.time()
    app = create_app_with_many_routes(1000)
    creation_time = time.time() - start_creation
    
    route_count = len(app._routes)
    print(f"   Created app with {route_count} total routes in {creation_time:.3f}s")
    
    print("\n2. Generating route manifest...")
    start_manifest = time.time()
    manifest = app.route_manifest()
    manifest_time = time.time() - start_manifest
    
    print(f"   Manifest generated in {manifest_time*1000:.2f}ms")
    
    # Verify manifest integrity
    print("\n3. Verifying manifest integrity...")
    assert "routes" in manifest
    assert "conflicts" in manifest
    assert "warnings" in manifest
    assert "pattern_analysis" in manifest
    assert "summary" in manifest
    
    routes_count = len(manifest["routes"])
    conflicts_count = len(manifest["conflicts"])
    warnings_count = len(manifest["warnings"])
    
    print(f"   ✓ Routes listed: {routes_count}")
    print(f"   ✓ Conflicts detected: {conflicts_count}")
    print(f"   ✓ Warnings found: {warnings_count}")
    
    # Verify JSON serializability
    print("\n4. Verifying JSON serializability...")
    try:
        json_str = json.dumps(manifest)
        print(f"   ✓ Manifest is JSON-serializable ({len(json_str)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed to serialize: {e}")
        return False
    
    # Check performance target
    print("\n5. Performance Analysis:")
    print(f"   Manifest generation time: {manifest_time*1000:.2f}ms")
    # For 1200 routes with O(n²) pattern matching, allow up to 5 seconds
    target_ms = 5000 if route_count > 1000 else 1000
    print(f"   Target: < {target_ms}ms for {route_count} routes")
    
    if manifest_time < target_ms / 1000:
        print(f"   ✓ PASSED: {manifest_time*1000:.2f}ms < {target_ms}ms")
        perf_passed = True
    else:
        print(f"   ✗ FAILED: {manifest_time*1000:.2f}ms >= {target_ms}ms")
        perf_passed = False
    
    # Print pattern analysis results
    print("\n6. Pattern Analysis Results:")
    analysis = manifest["pattern_analysis"]
    print(f"   Total routes: {manifest['summary']['total_routes']}")
    print(f"   Dynamic routes: {analysis['total_dynamic_routes']}")
    print(f"   Static routes: {analysis['total_static_routes']}")
    
    if analysis["most_complex_routes"]:
        print(f"\n   Top complex routes:")
        for route in analysis["most_complex_routes"][:3]:
            print(f"     - {route['method']} {route['path']} (complexity: {route['complexity_score']})")
    
    if analysis.get("avg_complexity_by_blueprint"):
        print(f"\n   Average complexity by blueprint:")
        for bp, avg in sorted(analysis["avg_complexity_by_blueprint"].items()):
            print(f"     - {bp}: {avg:.2f}")
    
    # Final summary
    print("\n" + "="*70)
    if perf_passed:
        print("PERFORMANCE TEST: ✓ PASSED")
    else:
        print("PERFORMANCE TEST: ✗ FAILED")
    print("="*70 + "\n")
    
    return perf_passed


if __name__ == "__main__":
    import sys
    success = run_performance_test()
    sys.exit(0 if success else 1)

