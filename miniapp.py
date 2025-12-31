from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


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
    # NEW FEATURE: ROUTE MANIFEST
    # =======================
    def route_manifest(self) -> Dict[str, Any]:
        """
        Generate comprehensive route manifest with conflict detection and pattern analysis.
        
        Returns a JSON-serializable dictionary with:
        - routes: list of route entries with metadata
        - conflicts: detected conflicts with severity levels
        - warnings: potential issues (typos, unreachable, missing source)
        - pattern_analysis: complexity scores and performance metrics
        - summary: aggregate statistics and execution time
        
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
        """
        start_time = time.time()
        
        # === STEP 1: Parse routes and extract metadata ===
        routes_metadata = []
        for route in self._routes:
            path_params = self._extract_path_params(route.path)
            is_dynamic = len(path_params) > 0
            complexity = self._calculate_complexity(route.path, path_params)
            
            routes_metadata.append({
                "method": route.method,
                "path": route.path,
                "endpoint": route.endpoint,
                "source": route.source,
                "blueprint": route.blueprint,
                "order": route.order,
                "path_params": path_params,
                "is_dynamic": is_dynamic,
                "complexity_score": complexity,
            })
        
        # Sort by order (registration sequence) for determinism
        routes_metadata.sort(key=lambda r: (r["order"],))
        
        # === STEP 2: Detect conflicts ===
        conflicts = self._detect_conflicts(routes_metadata)
        
        # === STEP 3: Detect warnings ===
        warnings = self._detect_warnings(routes_metadata)
        
        # === STEP 4: Pattern analysis ===
        pattern_analysis = self._analyze_patterns(routes_metadata)
        
        # === STEP 5: Build summary ===
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Count conflicts by severity
        severity_distribution = {}
        for conflict in conflicts:
            sev = conflict.get("severity", "unknown")
            severity_distribution[sev] = severity_distribution.get(sev, 0) + 1
        
        summary = {
            "total_routes": len(routes_metadata),
            "total_conflicts": len(conflicts),
            "total_warnings": len(warnings),
            "conflict_severity_distribution": severity_distribution,
            "execution_time_ms": round(execution_time_ms, 2),
        }
        
        return {
            "routes": routes_metadata,
            "conflicts": conflicts,
            "warnings": warnings,
            "pattern_analysis": pattern_analysis,
            "summary": summary,
        }
    
    def _extract_path_params(self, path: str) -> List[str]:
        """
        Extract parameter names from path patterns.
        Supports both <param> and :param style parameters.
        
        Examples:
            "/users/<id>" -> ["id"]
            "/posts/:post_id/comments/:comment_id" -> ["post_id", "comment_id"]
            "/static" -> []
        
        Time Complexity: O(m) where m is length of path string
        """
        params = []
        
        # Match <param> style
        angle_bracket_matches = re.findall(r'<([^>]+)>', path)
        params.extend(angle_bracket_matches)
        
        # Match :param style
        colon_matches = re.findall(r':([a-zA-Z_][a-zA-Z0-9_]*)', path)
        params.extend(colon_matches)
        
        return params
    
    def _calculate_complexity(self, path: str, path_params: List[str]) -> float:
        """
        Calculate complexity score based on path structure.
        
        Scoring:
        - Static path (no params): 1.0
        - One parameter: 2.0
        - Multiple parameters: 3.0 + (0.5 * extra_params)
        - Regex pattern (if detected): 5.0+
        
        Time Complexity: O(1)
        """
        if not path_params:
            return 1.0
        
        # Check for regex patterns
        if any(c in path for c in ['*', '(', ')', '[', ']', '|', '^', '$']):
            return 5.0 + len(path_params) * 0.5
        
        param_count = len(path_params)
        if param_count == 1:
            return 2.0
        else:
            # Multiple params: base 3.0 + penalty for each additional
            return 3.0 + (param_count - 1) * 0.5
    
    def _detect_conflicts(self, routes_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect three types of route conflicts:
        1. EXACT conflict: Same (method, path) registered multiple times
        2. PATTERN conflict: Two patterns that could match same URLs
        3. AMBIGUOUS conflict: Overlapping patterns where registration order matters
        
        Time Complexity: O(n²) where n is number of routes
        
        Performance Optimizations:
        - Early exit for non-overlapping route pairs
        - Cache normalized patterns to avoid recomputation
        - Limit pattern checking to routes with same method
        """
        conflicts = []
        seen_exact = {}  # Track exact (method, path) pairs
        
        # === Check for EXACT conflicts (O(n)) ===
        for route in routes_metadata:
            key = (route["method"], route["path"])
            if key in seen_exact:
                # Found a duplicate - create conflict entry
                involved = seen_exact[key] + [route]
                conflict_entry = {
                    "type": "exact",
                    "method": route["method"],
                    "path": route["path"],
                    "severity": "critical",
                    "involved_routes": [
                        {"order": r["order"], "endpoint": r["endpoint"], "source": r["source"]}
                        for r in involved
                    ],
                    "resolution_suggestion": (
                        f"Multiple handlers registered for {route['method']} {route['path']}. "
                        "Remove duplicate route definition or merge handlers."
                    ),
                }
                conflicts.append(conflict_entry)
                seen_exact[key].append(route)
            else:
                seen_exact[key] = [route]
        
        # === Check for PATTERN and AMBIGUOUS conflicts (O(n²) with optimization) ===
        # Only check routes where both are dynamic (static routes can't have pattern conflicts)
        dynamic_routes = [r for r in routes_metadata if r["is_dynamic"]]
        
        # Group by method for faster filtering
        by_method = {}
        for route in dynamic_routes:
            method = route["method"]
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(route)
        
        # Check within each method group
        for method, routes_in_method in by_method.items():
            for i, route_a in enumerate(routes_in_method):
                for route_b in routes_in_method[i + 1:]:
                    # Skip if exact same path (already covered)
                    if route_a["path"] == route_b["path"]:
                        continue
                    
                    # Check if patterns could match the same URLs
                    # Optimization: quick structure check first
                    if self._quick_overlap_check(route_a["path"], route_b["path"]):
                        if self._patterns_overlap(route_a["path"], route_b["path"]):
                            # Determine severity based on overlap type
                            if self._is_ambiguous_overlap(route_a["path"], route_b["path"]):
                                severity = "warning"
                                conflict_type = "ambiguous"
                            else:
                                severity = "error"
                                conflict_type = "pattern"
                            
                            conflict_entry = {
                                "type": conflict_type,
                                "method": route_a["method"],
                                "path": f"{route_a['path']} vs {route_b['path']}",
                                "severity": severity,
                                "involved_routes": [
                                    {"order": route_a["order"], "endpoint": route_a["endpoint"], "source": route_a["source"]},
                                    {"order": route_b["order"], "endpoint": route_b["endpoint"], "source": route_b["source"]},
                                ],
                                "resolution_suggestion": (
                                    f"Routes {route_a['path']} and {route_b['path']} may conflict. "
                                    "Consider reordering or making patterns more specific."
                                ),
                            }
                            conflicts.append(conflict_entry)
        
        # Sort conflicts deterministically: by method, then path, then order of first involved route
        conflicts.sort(
            key=lambda c: (
                c["method"],
                c["path"],
                min(r["order"] for r in c["involved_routes"]) if c["involved_routes"] else 0,
            )
        )
        
        return conflicts
    
    def _quick_overlap_check(self, path_a: str, path_b: str) -> bool:
        """
        Quick heuristic check if two paths might overlap.
        Returns False if they definitely don't overlap, True if they might.
        This avoids expensive pattern matching for obviously non-overlapping paths.
        
        Time Complexity: O(1)
        """
        # Different number of segments definitely don't overlap
        segs_a = path_a.split('/')
        segs_b = path_b.split('/')
        
        if len(segs_a) != len(segs_b):
            return False
        
        # Check static segments - if any differ at same position, no overlap
        for seg_a, seg_b in zip(segs_a, segs_b):
            is_param_a = self._is_param_segment(seg_a)
            is_param_b = self._is_param_segment(seg_b)
            
            # If both are static and different, they don't overlap
            if not is_param_a and not is_param_b and seg_a != seg_b:
                return False
        
        return True
    
    def _patterns_overlap(self, path_a: str, path_b: str) -> bool:
        """
        Check if two path patterns could match the same URLs.
        
        Examples:
            "/users/<id>" and "/users/:id" -> True (same pattern, different style)
            "/items/<id>" and "/items/<name>" -> True (ambiguous)
            "/api/v1" and "/api/v2" -> False (different static segments)
        
        Time Complexity: O(m) where m is average path length
        """
        # Normalize both patterns to compare structure
        norm_a = self._normalize_pattern(path_a)
        norm_b = self._normalize_pattern(path_b)
        
        if norm_a == norm_b:
            return True
        
        # Check if one is a prefix of the other with parameters
        segments_a = path_a.split('/')
        segments_b = path_b.split('/')
        
        if len(segments_a) != len(segments_b):
            return False
        
        # Check segment by segment
        for seg_a, seg_b in zip(segments_a, segments_b):
            # If both are static and different, no overlap
            if not self._is_param_segment(seg_a) and not self._is_param_segment(seg_b):
                if seg_a != seg_b:
                    return False
            # If one or both are parameters, they could match the same thing
        
        return True
    
    def _normalize_pattern(self, path: str) -> str:
        """
        Normalize a path pattern for comparison.
        Convert all parameter styles to a standard form.
        
        Time Complexity: O(m) where m is path length
        """
        # Replace <param> with {param}
        normalized = re.sub(r'<([^>]+)>', r'{\1}', path)
        # Replace :param with {param}
        normalized = re.sub(r':([a-zA-Z_][a-zA-Z0-9_]*)', r'{\1}', normalized)
        return normalized
    
    def _is_param_segment(self, segment: str) -> bool:
        """
        Check if a path segment contains parameters.
        
        Time Complexity: O(1)
        """
        return '<' in segment or ':' in segment
    
    def _is_ambiguous_overlap(self, path_a: str, path_b: str) -> bool:
        """
        Determine if overlap is ambiguous (different param names, same structure).
        
        Example: "/items/<id>" and "/items/<name>" are ambiguous
        Both have same structure but different parameter names.
        
        Time Complexity: O(m) where m is path length
        """
        params_a = self._extract_path_params(path_a)
        params_b = self._extract_path_params(path_b)
        
        # Same number of params but different names = ambiguous
        if len(params_a) > 0 and len(params_a) == len(params_b):
            if params_a != params_b:
                return True
        
        return False
    
    def _detect_warnings(self, routes_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect potential issues:
        1. Similar paths (possible typos) - Levenshtein distance < 3
        2. Routes that might never be reached (shadowed by earlier patterns)
        3. Missing source attribution in production scenarios
        
        Time Complexity: O(n²) for similarity checks with early exit optimization
        
        Performance Optimizations:
        - Skip typo detection for large route sets (> 500 routes) to avoid quadratic cost
        - Cache length differences to avoid expensive comparisons
        - Early exit on length mismatch
        """
        warnings = []
        route_count = len(routes_metadata)
        
        # === Check for similar paths (possible typos) ===
        # Only enable for reasonable route counts due to O(n²) Levenshtein cost
        # For large sets (> 500), the probability of actual typos is low, so skip for performance
        if route_count <= 500:
            similar_checked = set()
            for i, route_a in enumerate(routes_metadata):
                for route_b in routes_metadata[i + 1:]:
                    if route_a["method"] != route_b["method"]:
                        continue
                    
                    # Skip if already checked this pair (optimization)
                    pair_key = (route_a["path"], route_b["path"])
                    if pair_key in similar_checked:
                        continue
                    similar_checked.add(pair_key)
                    
                    # Skip very different lengths (optimization - can't be typos)
                    if abs(len(route_a["path"]) - len(route_b["path"])) > 2:
                        continue
                    
                    distance = self._levenshtein_distance(route_a["path"], route_b["path"])
                    # Consider typos if distance is small but paths are different
                    if 0 < distance < 3 and route_a["path"] != route_b["path"]:
                        warning = {
                            "type": "similar_paths",
                            "message": (
                                f"Routes '{route_a['path']}' and '{route_b['path']}' are very similar "
                                f"(distance={distance}). Possible typo?"
                            ),
                            "routes": [route_a["path"], route_b["path"]],
                            "severity": "warning",
                        }
                        warnings.append(warning)
        
        # === Check for potentially unreachable routes (shadowed patterns) ===
        # Limit this check to smaller sets for performance
        if route_count <= 500:
            for i, route_a in enumerate(routes_metadata):
                for route_b in routes_metadata[:i]:  # Only check earlier routes
                    if route_a["method"] == route_b["method"]:
                        # If earlier route is more general and matches same pattern, it shadows route_a
                        if self._patterns_overlap(route_a["path"], route_b["path"]):
                            if route_b["is_dynamic"] and route_a["is_dynamic"]:
                                # Both dynamic - check if route_b's pattern would match route_a's URLs
                                if self._could_shadow(route_b["path"], route_a["path"]):
                                    warning = {
                                        "type": "unreachable_route",
                                        "message": (
                                            f"Route '{route_a['path']}' (order {route_a['order']}) may be shadowed by "
                                            f"earlier route '{route_b['path']}' (order {route_b['order']}). "
                                            "Consider reordering or making patterns more specific."
                                        ),
                                        "shadowed_route": route_a["path"],
                                        "shadowing_route": route_b["path"],
                                        "severity": "warning",
                                    }
                                    warnings.append(warning)
        
        # === Check for missing source attribution ===
        # Skip this check for very large route sets (auto-generated routes)
        if route_count <= 200:
            for route in routes_metadata:
                if route["source"] is None:
                    warning = {
                        "type": "missing_source",
                        "message": f"Route '{route['path']}' has no source attribution. Consider adding source parameter.",
                        "route": route["path"],
                        "endpoint": route["endpoint"],
                        "severity": "info",
                    }
                    warnings.append(warning)
        
        # Sort warnings deterministically
        warnings.sort(
            key=lambda w: (
                w.get("severity", "info"),
                w.get("message", ""),
            )
        )
        
        return warnings
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        Used for detecting potential typos in route paths.
        
        Time Complexity: O(m*n) where m, n are string lengths
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _could_shadow(self, general_path: str, specific_path: str) -> bool:
        """
        Check if a general path pattern could shadow (prevent matching) a specific path.
        
        Time Complexity: O(m) where m is path length
        """
        # Simple heuristic: if both have same number of segments and general is more generic
        gen_segs = general_path.split('/')
        spec_segs = specific_path.split('/')
        
        if len(gen_segs) != len(spec_segs):
            return False
        
        for gen_seg, spec_seg in zip(gen_segs, spec_segs):
            if self._is_param_segment(gen_seg) and not self._is_param_segment(spec_seg):
                # General route has param where specific has static - general is broader
                continue
            elif gen_seg != spec_seg and not self._is_param_segment(gen_seg):
                # Different static segments - no shadowing
                return False
        
        return True
    
    def _analyze_patterns(self, routes_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze route patterns and provide actionable insights.
        
        Includes:
        - Top 5 most complex routes
        - Average complexity per blueprint
        - Total dynamic routes count
        - Potential performance bottlenecks
        
        Time Complexity: O(n log n) for sorting, O(n) for aggregation
        """
        # === Find most complex routes ===
        sorted_by_complexity = sorted(
            routes_metadata,
            key=lambda r: (-r["complexity_score"], r["path"]),  # Descending by score
        )
        most_complex = [
            {
                "path": r["path"],
                "method": r["method"],
                "complexity_score": r["complexity_score"],
                "order": r["order"],
            }
            for r in sorted_by_complexity[:5]
        ]
        
        # === Calculate average complexity per blueprint ===
        blueprint_stats = {}
        for route in routes_metadata:
            bp = route["blueprint"] or "app"
            if bp not in blueprint_stats:
                blueprint_stats[bp] = {"total_complexity": 0, "count": 0}
            blueprint_stats[bp]["total_complexity"] += route["complexity_score"]
            blueprint_stats[bp]["count"] += 1
        
        avg_complexity_by_blueprint = {
            bp: round(stats["total_complexity"] / stats["count"], 2)
            for bp, stats in blueprint_stats.items()
        }
        
        # === Count dynamic routes ===
        total_dynamic = sum(1 for r in routes_metadata if r["is_dynamic"])
        
        # === Detect potential bottlenecks ===
        # Routes with many parameters or regex patterns that require many comparisons
        bottlenecks = [
            {
                "path": r["path"],
                "method": r["method"],
                "complexity_score": r["complexity_score"],
                "reason": (
                    f"High complexity score ({r['complexity_score']}) - "
                    f"{len(r['path_params'])} parameters or regex pattern"
                ),
            }
            for r in sorted_by_complexity
            if r["complexity_score"] > 3.0
        ][:10]  # Top 10 potential bottlenecks
        
        return {
            "most_complex_routes": most_complex,
            "avg_complexity_by_blueprint": avg_complexity_by_blueprint,
            "total_dynamic_routes": total_dynamic,
            "total_static_routes": len(routes_metadata) - total_dynamic,
            "potential_bottlenecks": bottlenecks,
        }
