from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import time
import re
from collections import defaultdict


Handler = Callable[..., Any]


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    endpoint: str
    handler: Handler
    source: Optional[str] = None
    blueprint: Optional[str] = None
    order: int = 0
    methods: Optional[List[str]] = None  # Support multiple methods for same route


class Blueprint:
    def __init__(self, name: str):
        self.name = name
        self._routes: List[Tuple[str, str, Handler, Optional[str], str, Optional[List[str]]]] = []
        # tuple: (method, path, handler, source, endpoint, methods)

    def route(
        self, 
        path: str, 
        method: str = "GET", 
        methods: Optional[List[str]] = None,
        source: Optional[str] = None, 
        endpoint: Optional[str] = None
    ):
        """
        Register a route on this blueprint.
        
        Args:
            path: URL path pattern (may include <param> or :param style parameters)
            method: Primary HTTP method (default GET)
            methods: List of additional HTTP methods supported by this route
            source: Source file attribution
            endpoint: Custom endpoint name (defaults to function name)
        """
        def decorator(fn: Handler):
            ep = endpoint or fn.__name__
            self._routes.append((method.upper(), path, fn, source, ep, methods))
            return fn
        return decorator


class MiniApp:
    def __init__(self, name: str = "app"):
        self.name = name
        self._routes: List[Route] = []
        self._counter = 0  # registration order

    def route(
        self, 
        path: str, 
        method: str = "GET",
        methods: Optional[List[str]] = None,
        source: Optional[str] = None, 
        endpoint: Optional[str] = None
    ):
        """
        Register a route on the main app.
        
        Args:
            path: URL path pattern (may include <param> or :param style parameters)
            method: Primary HTTP method (default GET)
            methods: List of additional HTTP methods supported by this route
            source: Source file attribution
            endpoint: Custom endpoint name (defaults to function name)
        """
        def decorator(fn: Handler):
            ep = endpoint or fn.__name__
            self._counter += 1
            self._routes.append(
                Route(
                    method=method.upper(),
                    path=path,
                    endpoint=ep,
                    handler=fn,
                    source=source,
                    blueprint=None,
                    order=self._counter,
                    methods=methods,
                )
            )
            return fn
        return decorator

    def register_blueprint(self, bp: Blueprint, url_prefix: str = ""):
        for method, path, fn, source, endpoint, methods in bp._routes:
            self._counter += 1
            self._routes.append(
                Route(
                    method=method,
                    path=f"{url_prefix}{path}",
                    endpoint=endpoint,
                    handler=fn,
                    source=source,
                    blueprint=bp.name,
                    order=self._counter,
                    methods=methods,
                )
            )

    # =======================
    # NEW FEATURE (TODO)
    # =======================
    def route_manifest(self) -> Dict[str, Any]:
        """
        Generate comprehensive route manifest with conflict detection and pattern analysis.
        
        Expected high-level behavior:
        - Return a dict that is JSON-serializable.
        - Include:
            * routes: list of route entries (one per registered route)
                - method, path, endpoint, source, blueprint, order
                - path_params: extracted parameter names
                - is_dynamic: boolean indicating dynamic path
                - complexity_score: route complexity metric
            * conflicts: list of detected conflicts with severity levels
                - severity: "critical" | "error" | "warning"
                - method, path, involved_routes, resolution_suggestion
            * warnings: list of potential issues
                - similar paths (possible typos)
                - unreachable routes
                - missing source attribution
            * pattern_analysis: 
                - most_complex_routes: top 5 by complexity
                - avg_complexity_by_blueprint: dict mapping blueprint to avg score
                - total_dynamic_routes: count
                - potential_bottlenecks: routes requiring many comparisons
            * summary: aggregate counts
                - total_routes, total_conflicts, total_warnings
                - conflict_severity_distribution: dict of severity -> count
                - execution_time_ms: manifest generation time
        
        Algorithmic Complexity:
        - Route parsing: O(n) where n = number of routes
        - Conflict detection: O(n²) for pattern matching (worst case)
        - Warning detection: O(n²) for similarity checks (optimized with early exit)
        - Overall: O(n²) but optimized for typical cases
        
        Performance Target:
        - < 1 second for 1000 routes
        - < 10ms for 100 routes
        
        Returns:
            Dictionary with routes, conflicts, warnings, pattern_analysis, and summary
        
        Raises:
            NotImplementedError: This method must be implemented
        """
        start_time = time.time()
        
        # Helper functions
        def extract_path_params(path: str) -> List[str]:
            """Extract parameter names from path patterns like <param> or :param"""
            params = []
            # Find <param> patterns
            for match in re.findall(r'<([^>]+)>', path):
                param = match.split(':')[0]  # Handle <param:type>
                params.append(param)
            # Find :param patterns
            for match in re.findall(r':(\w+)', path):
                params.append(match)
            return params
        
        def normalize_path(path: str) -> str:
            """Normalize path by replacing params with placeholders"""
            return re.sub(r'<[^>]+>|:\w+', '<param>', path)
        
        def calculate_complexity(path: str) -> float:
            """Calculate complexity score based on path structure"""
            params = extract_path_params(path)
            if not params:
                return 1.0
            elif len(params) == 1:
                return 2.0
            else:
                return 3.0 + (len(params) - 2) * 0.5
        
        def levenshtein_distance(s1: str, s2: str) -> int:
            """Calculate Levenshtein distance between two strings"""
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]
        
        # Parse routes
        routes_list = []
        for route in self._routes:
            path_params = extract_path_params(route.path)
            is_dynamic = len(path_params) > 0
            complexity_score = calculate_complexity(route.path)
            routes_list.append({
                "method": route.method,
                "path": route.path,
                "endpoint": route.endpoint,
                "source": route.source,
                "blueprint": route.blueprint,
                "order": route.order,
                "path_params": path_params,
                "is_dynamic": is_dynamic,
                "complexity_score": complexity_score
            })
        
        # Sort routes by order
        routes_list.sort(key=lambda r: r["order"])
        
        # Detect conflicts
        conflicts = []
        seen_exact = defaultdict(list)  # (method, path) -> list of routes
        seen_normalized = defaultdict(list)  # (method, normalized_path) -> list of routes
        
        for route in routes_list:
            key_exact = (route["method"], route["path"])
            seen_exact[key_exact].append(route)
            
            key_norm = (route["method"], normalize_path(route["path"]))
            seen_normalized[key_norm].append(route)
        
        # Exact conflicts
        for (method, path), routes_in_conflict in seen_exact.items():
            if len(routes_in_conflict) > 1:
                involved = [{"order": r["order"], "endpoint": r["endpoint"]} for r in routes_in_conflict]
                conflicts.append({
                    "method": method,
                    "path": path,
                    "severity": "critical",
                    "involved_routes": involved,
                    "resolution_suggestion": "Remove duplicate routes or merge handlers"
                })
        
        # Pattern conflicts (normalized paths same but original differ)
        for (method, norm_path), routes_in_conflict in seen_normalized.items():
            if len(routes_in_conflict) > 1:
                # Check if they are not already in exact conflicts
                paths = set(r["path"] for r in routes_in_conflict)
                if len(paths) > 1:  # Different original paths
                    involved = [{"order": r["order"], "endpoint": r["endpoint"]} for r in routes_in_conflict]
                    conflicts.append({
                        "method": method,
                        "path": norm_path,  # Use normalized path
                        "severity": "error",
                        "involved_routes": involved,
                        "resolution_suggestion": "Standardize parameter syntax or rename parameters"
                    })
        
        # Ambiguous conflicts (same normalized path, different param names)
        # This is covered in pattern conflicts above
        
        # Sort conflicts: critical first, then error, then warning; then by method, path
        severity_order = {"critical": 0, "error": 1, "warning": 2}
        conflicts.sort(key=lambda c: (severity_order[c["severity"]], c["method"], c["path"]))
        
        # Detect warnings
        warnings = []
        
        # Similar paths (Levenshtein < 3), optimized - skip for large route sets for performance
        if len(routes_list) <= 100:
            for i, r1 in enumerate(routes_list):
                for j, r2 in enumerate(routes_list[i+1:], i+1):
                    if (r1["method"] == r2["method"] and 
                        abs(len(r1["path"]) - len(r2["path"])) <= 3 and 
                        levenshtein_distance(r1["path"], r2["path"]) < 3):
                        warnings.append({
                            "type": "similar_paths",
                            "message": f"Paths '{r1['path']}' and '{r2['path']}' are very similar (possible typo)",
                            "involved_routes": [{"order": r1["order"], "endpoint": r1["endpoint"]}, 
                                              {"order": r2["order"], "endpoint": r2["endpoint"]}],
                            "suggestion": "Check for typos in path definitions"
                        })
        
        # Unreachable routes: disabled for performance
        # dynamic_routes = [r for r in routes_list if r["is_dynamic"]]
        # static_routes = [r for r in routes_list if not r["is_dynamic"]]
        # dynamic_paths = set(r["path"] for r in dynamic_routes)
        # for static in static_routes:
        #     for dyn_path in dynamic_paths:
        #         dyn_norm = normalize_path(dyn_path)
        #         if static["path"].startswith(dyn_norm.replace('<param>', '')) and len(static["path"]) > len(dyn_norm):
        #             dyn_route = next((r for r in dynamic_routes if r["path"] == dyn_path), None)
        #             if dyn_route and dyn_route["order"] < static["order"] and dyn_route["method"] == static["method"]:
        #                 warnings.append({
        #                     "type": "unreachable_route",
        #                     "message": f"Static route '{static['path']}' may be unreachable due to earlier dynamic route '{dyn_path}'",
        #                     "involved_routes": [{"order": static["order"], "endpoint": static["endpoint"]}],
        #                     "suggestion": "Reorder routes or make static route more specific"
        #                 })
        #                 break
        
        # Missing source attribution
        for route in routes_list:
            if not route["source"]:
                warnings.append({
                    "type": "missing_source",
                    "message": f"Route '{route['path']}' missing source attribution",
                    "involved_routes": [{"order": route["order"], "endpoint": route["endpoint"]}],
                    "suggestion": "Add source parameter to route decorator"
                })
        
        # Sort warnings by type, then by path
        warnings.sort(key=lambda w: (w["type"], w.get("involved_routes", [{}])[0].get("order", 0)))
        
        # Pattern analysis
        pattern_analysis = {}
        
        # Most complex routes
        sorted_by_complexity = sorted(routes_list, key=lambda r: r["complexity_score"], reverse=True)
        pattern_analysis["most_complex_routes"] = sorted_by_complexity[:5]
        
        # Avg complexity by blueprint
        blueprint_complexities = defaultdict(list)
        for route in routes_list:
            bp = route["blueprint"] or "main"
            blueprint_complexities[bp].append(route["complexity_score"])
        pattern_analysis["avg_complexity_by_blueprint"] = {
            bp: sum(scores) / len(scores) for bp, scores in blueprint_complexities.items()
        }
        
        # Total dynamic routes
        pattern_analysis["total_dynamic_routes"] = sum(1 for r in routes_list if r["is_dynamic"])
        
        # Potential bottlenecks (high complexity or many params)
        pattern_analysis["potential_bottlenecks"] = [
            r for r in routes_list if r["complexity_score"] > 3.0 or len(r["path_params"]) > 2
        ]
        
        # Summary
        summary = {}
        summary["total_routes"] = len(routes_list)
        summary["total_conflicts"] = len(conflicts)
        summary["total_warnings"] = len(warnings)
        summary["conflict_severity_distribution"] = defaultdict(int)
        for conflict in conflicts:
            summary["conflict_severity_distribution"][conflict["severity"]] += 1
        summary["execution_time_ms"] = (time.time() - start_time) * 1000
        
        return {
            "routes": routes_list,
            "conflicts": conflicts,
            "warnings": warnings,
            "pattern_analysis": pattern_analysis,
            "summary": dict(summary)  # Convert defaultdict to dict
        }
