#!/usr/bin/env python3
"""
Generate sample manifest JSON for documentation
"""

from miniapp import MiniApp, Blueprint
import json

def create_sample_app():
    app = MiniApp("sample_app")
    
    # Simple routes
    @app.route("/health", method="GET", source="app.py")
    def health():
        return "ok"
    
    @app.route("/users", method="GET", source="users.py")
    def list_users():
        return []
    
    # Dynamic routes
    @app.route("/users/<user_id>", method="GET", source="users.py")
    def get_user():
        return {}
    
    @app.route("/posts/:post_id/comments/:comment_id", method="GET", source="posts.py")
    def get_comment():
        return {}
    
    # Blueprint
    api_bp = Blueprint("api")
    @api_bp.route("/status", method="GET", source="api.py")
    def api_status():
        return "api ok"
    
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Conflicts
    @app.route("/conflict", method="GET", source="a.py")
    def conflict_a():
        return "a"
    
    @app.route("/conflict", method="GET", source="b.py")
    def conflict_b():
        return "b"
    
    # Similar paths
    @app.route("/api/user", method="GET", source="similar.py")
    def user_profile():
        return {}
    
    @app.route("/api/users", method="GET", source="similar.py")
    def users_list():
        return []
    
    return app

if __name__ == "__main__":
    app = create_sample_app()
    manifest = app.route_manifest()
    
    with open("sample_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    print("Sample manifest saved to sample_manifest.json")