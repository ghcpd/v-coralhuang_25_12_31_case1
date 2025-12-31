from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


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
        """Generate a deterministic, JSON-serializable manifest of registered routes.

        Complexity:
        - Parsing routes: O(n)
        - Pairwise pattern/conflict checks: O(n^2) worst-case (n = number of routes)
        - Overall: O(n^2) worst-case but typical workloads remain fast.

        Determinism / sorting rules (tie-breakers):
        - Routes list is sorted by (path, method, order) lexicographically.
        - Conflicts/warnings are sorted by (severity, method, path, first_involved_order).
        - All tie-breakers use registration `order` to guarantee stable output.

        Returns a dict with keys: routes, conflicts, warnings, pattern_analysis, summary.
        """
        import re
        import time
        from collections import defaultdict

        start = time.perf_counter()

        # Helper: extract path parameters for both '<param>' and ':param' styles
        param_re_angle = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_]*)>")
        param_re_colon = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")

        def extract_params(path: str) -> List[str]:
            return list(dict.fromkeys(param_re_angle.findall(path) + param_re_colon.findall(path)))

        def is_dynamic(path: str) -> bool:
            return bool(param_re_angle.search(path) or param_re_colon.search(path) or "(" in path or ")" in path)

        # Complexity scoring heuristic
        def complexity_score(path: str) -> float:
            params = extract_params(path)
            score = 1.0  # base for static
            if "(" in path or ")" in path or "regex" in path:
                # treat explicit regex-like patterns as very complex
                score = max(score, 5.0)
            if len(params) == 1:
                score = max(score, 2.0)
            elif len(params) >= 2:
                score = max(score, 3.0 + 0.1 * (len(params) - 2))
            # small penalty for deep/static segments
            depth = len([p for p in path.split("/") if p])
            score += min(depth * 0.05, 0.5)
            return round(score, 3)

        # Simple path normalization for pattern comparisons
        def normalize_pattern(path: str) -> str:
            # convert :param and <param> to a generic token
            p = param_re_angle.sub("<param>", path)
            p = param_re_colon.sub("<param>", p)
            return p

        # Levenshtein distance (optimized small implementation)
        def levenshtein(a: str, b: str) -> int:
            if a == b:
                return 0
            if len(a) < len(b):
                a, b = b, a
            previous = list(range(len(b) + 1))
            for i, ca in enumerate(a, start=1):
                current = [i]
                for j, cb in enumerate(b, start=1):
                    insertions = previous[j] + 1
                    deletions = current[j - 1] + 1
                    substitutions = previous[j - 1] + (ca != cb)
                    current.append(min(insertions, deletions, substitutions))
                previous = current
            return previous[-1]

        # Build route entries
        routes_out: List[Dict[str, Any]] = []
        for r in self._routes:
            params = extract_params(r.path)
            dynamic = is_dynamic(r.path)
            cs = complexity_score(r.path)
            routes_out.append(
                {
                    "method": r.method,
                    "path": r.path,
                    "endpoint": r.endpoint,
                    "source": r.source if r.source is not None else None,
                    "blueprint": r.blueprint if r.blueprint is not None else None,
                    "order": r.order,
                    "path_params": params,
                    "is_dynamic": dynamic,
                    "complexity_score": cs,
                }
            )

        # Deterministic sort: path, method, order
        routes_out.sort(key=lambda x: (x["path"], x["method"], x["order"]))

        # Conflict detection
        conflicts: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # Index by (method, path) for exact conflict detection
        exact_index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        pattern_index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

        for entry in routes_out:
            exact_index[(entry["method"], entry["path"])].append(entry)
            pattern_index[(entry["method"], normalize_pattern(entry["path"]))].append(entry)

        # EXACT conflicts
        for (method, path), group in exact_index.items():
            if len(group) > 1:
                involved = [{"order": g["order"], "endpoint": g["endpoint"]} for g in group]
                conflicts.append(
                    {
                        "method": method,
                        "path": path,
                        "severity": "critical",
                        "involved_routes": sorted(involved, key=lambda x: x["order"]),
                        "resolution_suggestion": "Remove duplicate registrations or merge handlers; ensure unique (method,path)",
                    }
                )

        # PATTERN conflicts: use precomputed buckets to avoid O(n^2)
        def shape(p: str) -> Tuple[str, ...]:
            parts = [seg for seg in p.split("/") if seg]
            return tuple("<param>" if param_re_angle.match(seg) or param_re_colon.match(seg) else seg for seg in parts)

        # PATTERN conflict detection via normalized pattern buckets
        for (method, norm), group in pattern_index.items():
            if len(group) > 1:
                # if raw paths differ but normalized equal -> pattern conflict
                raw_paths = {g["path"] for g in group}
                if len(raw_paths) > 1:
                    involved = [{"order": g["order"], "endpoint": g["endpoint"]} for g in group]
                    conflicts.append(
                        {
                            "method": method,
                            "path": norm,
                            "severity": "error",
                            "involved_routes": sorted(involved, key=lambda x: x["order"]),
                            "resolution_suggestion": "Unify parameter syntax or make paths explicit to avoid pattern collisions",
                        }
                    )

        # AMBIGUOUS conflicts: same shape but different param names/endpoints
        shape_map: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
        for r in routes_out:
            shape_map[shape(r["path"])].append(r)
        for shape_key, group in shape_map.items():
            if len(group) > 1:
                # if there are entries with identical shape but different raw path -> ambiguous
                raw_paths = {g["path"] for g in group}
                if len(raw_paths) > 1:
                    involved = [{"order": g["order"], "endpoint": g["endpoint"]} for g in group]
                    conflicts.append(
                        {
                            "method": group[0]["method"],
                            "path": "/" + "/".join(shape_key),
                            "severity": "warning",
                            "involved_routes": sorted(involved, key=lambda x: x["order"]),
                            "resolution_suggestion": "Different parameter names at same positions are ambiguous; prefer distinct static segments or explicit regex",
                        }
                    )


        # Warnings: similar paths (possible typos)
        # For performance we only compare each path to a small neighborhood in sorted order
        path_list = sorted({r["path"] for r in routes_out})
        window = 3  # compare to next 3 neighbors; nearby lexicographic strings are likely similar
        for i in range(len(path_list)):
            for j in range(i + 1, min(i + 1 + window, len(path_list))):
                a = path_list[i]
                b = path_list[j]
                # cheap length filter
                if abs(len(a) - len(b)) > 4:
                    continue
                if levenshtein(a, b) < 3:
                    warnings.append(
                        {
                            "type": "similar_path",
                            "paths": (a, b),
                            "message": f"Paths '{a}' and '{b}' are very similar; possible typo",
                        }
                    )

        # Warning: missing source attribution in production scenarios (heuristic)
        for r in routes_out:
            if r["source"] is None:
                warnings.append(
                    {
                        "type": "missing_source",
                        "method": r["method"],
                        "path": r["path"],
                        "message": "Route has no source attribution",
                    }
                )

        # Pattern analysis: most complex routes (top 5), avg complexity per blueprint, potential bottlenecks
        total_dynamic = sum(1 for r in routes_out if r["is_dynamic"])
        most_complex = sorted(routes_out, key=lambda x: (-x["complexity_score"], x["order"]))[:5]

        avg_by_bp: Dict[str, float] = {}
        bp_groups: Dict[Optional[str], List[float]] = defaultdict(list)
        for r in routes_out:
            bp_groups[r["blueprint"]].append(r["complexity_score"])
        for bp, scores in bp_groups.items():
            avg_by_bp[bp if bp is not None else "<root>"] = round(sum(scores) / len(scores), 3)

        # Potential bottlenecks: routes that are dynamic and appear in many pairwise comparisons
        # Heuristic: dynamic routes with high complexity and many siblings with same prefix
        prefix_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in routes_out:
            parts = "/".join([seg for seg in r["path"].split("/") if seg][:2])  # first two segments
            prefix_map[parts].append(r)
        potential_bottlenecks = []
        for pref, group in prefix_map.items():
            if len(group) > 8:
                # many routes share prefix -> potential performance hotspot
                potential_bottlenecks.extend(
                    [{"path": g["path"], "complexity_score": g["complexity_score"]} for g in sorted(group, key=lambda x: (-x["complexity_score"], x["order"]))[:10]]
                )

        # Deduplicate similar warnings/conflicts deterministically (by sorted JSON representation)
        def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            seen = set()
            out = []
            import json
            for it in items:
                key = json.dumps(it, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    out.append(it)
            return out

        conflicts = dedupe(conflicts)
        warnings = dedupe(warnings)

        # Deterministic sort for conflicts and warnings
        severity_order = {"critical": 0, "error": 1, "warning": 2}
        conflicts.sort(key=lambda c: (severity_order.get(c.get("severity"), 99), c.get("method", ""), c.get("path", ""), c["involved_routes"][0]["order"]))
        warnings.sort(key=lambda w: (w.get("type", ""), w.get("method", ""), w.get("path", "") if "path" in w else ""))

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000.0

        summary = {
            "total_routes": len(routes_out),
            "total_conflicts": len(conflicts),
            "total_warnings": len(warnings),
            "conflict_severity_distribution": {
                "critical": sum(1 for c in conflicts if c.get("severity") == "critical"),
                "error": sum(1 for c in conflicts if c.get("severity") == "error"),
                "warning": sum(1 for c in conflicts if c.get("severity") == "warning"),
            },
            "execution_time_ms": round(elapsed_ms, 3),
        }

        manifest = {
            "routes": routes_out,
            "conflicts": conflicts,
            "warnings": warnings,
            "pattern_analysis": {
                "most_complex_routes": most_complex,
                "total_dynamic_routes": total_dynamic,
                "avg_complexity_by_blueprint": avg_by_bp,
                "potential_bottlenecks": potential_bottlenecks,
            },
            "summary": summary,
        }

        return manifest
