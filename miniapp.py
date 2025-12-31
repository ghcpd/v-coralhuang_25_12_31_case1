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
        """Generate a deterministic, JSON-serializable manifest describing registered routes.

        Complexity:
        - Let n = number of registered (method,path) route-entries after expanding method lists.
        - Building route entries: O(n).
        - Grouping / bucketed comparisons: average-case << O(n^2); worst-case pattern/conflict checks O(n^2).
        - Overall worst-case: O(n^2).

        Determinism / sorting rules (explicit):
        - Routes list is sorted by (path, method, order) lexicographically.
        - Conflicts/warnings are sorted by (severity_rank, method, path, first_involved_order).
        - pattern_analysis lists are sorted by score desc then order asc.
        - These tie-breakers ensure stable output for identical inputs.

        Returns a dict with keys: routes, conflicts, warnings, pattern_analysis, summary.
        """
        import re
        import time
        from collections import defaultdict

        start = time.perf_counter()
        _phase_ts = {"start": start}

        # --- helpers -----------------------------------------------------------------
        param_angle_re = re.compile(r"<([^/>]+)>")
        param_colon_re = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")

        def extract_params(path: str) -> List[str]:
            # find both <param> and :param styles
            names = []
            names += [m.group(1) for m in param_angle_re.finditer(path)]
            names += [m.group(1) for m in param_colon_re.finditer(path)]
            return names

        def is_dynamic_path(path: str) -> bool:
            return bool(param_angle_re.search(path) or param_colon_re.search(path) or "(" in path)

        def normalize_pattern(path: str) -> str:
            # Replace param tokens with {} placeholder; keep leading/trailing slashes
            p = param_angle_re.sub("{}", path)
            p = param_colon_re.sub("{}", p)
            # collapse multiple slashes
            p = re.sub(r"//+", "/", p)
            return p

        def path_tokens(path: str) -> List[str]:
            # split normalized pattern into path segments
            return [t for t in normalize_pattern(path).split("/") if t != ""]

        def complexity_score(path: str) -> float:
            # static=1.0, one param=2.0, multiple params incrementally higher, regex heavy=5.0+
            params = extract_params(path)
            score = 1.0
            if params:
                score = 1.0 + 1.0 * len(params)
            # penalty for deep paths
            depth = len([seg for seg in path.split("/") if seg])
            score += max(0.0, (depth - 2) * 0.1)
            # regex-like patterns (paren) are expensive
            if "(" in path and ")" in path:
                score = max(score, 5.0)
            return round(float(score), 3)

        def levenshtein_threshold(a: str, b: str, thresh: int = 2) -> int:
            """Return distance but stop early if > thresh to save time."""
            # early length check
            if abs(len(a) - len(b)) > thresh:
                return thresh + 1
            # classic DP with early stop
            la, lb = len(a), len(b)
            if la == 0:
                return lb
            if lb == 0:
                return la
            prev = list(range(lb + 1))
            for i in range(1, la + 1):
                cur = [i] + [0] * lb
                mini = cur[0]
                ai = a[i - 1]
                for j in range(1, lb + 1):
                    cost = 0 if ai == b[j - 1] else 1
                    cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
                    if cur[j] < mini:
                        mini = cur[j]
                if mini > thresh:
                    return thresh + 1
                prev = cur
            return prev[-1]

        def pattern_conflict(a: str, b: str) -> bool:
            # Two patterns conflict if their normalized tokens count equal and each token either equal
            # or one/both are placeholders {}. This is fast and conservative.
            ta = path_tokens(a)
            tb = path_tokens(b)
            if len(ta) != len(tb):
                return False
            for xa, xb in zip(ta, tb):
                if xa == xb:
                    continue
                if xa == "{}" or xb == "{}":
                    continue
                return False
            return True

        # severity ranking for deterministic ordering
        severity_rank = {"critical": 0, "error": 1, "warning": 2, "info": 3}

        # --- expand routes into per-method entries ---------------------------------
        expanded: List[Dict[str, Any]] = []
        for r in self._routes:
            methods = [r.method]
            if r.methods:
                # include additional methods, keep primary first
                for m in r.methods:
                    mu = m.upper()
                    if mu not in methods:
                        methods.append(mu)
            for m in methods:
                expanded.append(
                    {
                        "method": m.upper(),
                        "path": r.path,
                        "endpoint": r.endpoint,
                        "source": r.source,
                        "blueprint": r.blueprint,
                        "order": r.order,
                    }
                )

        # Build route entries with analysis
        routes: List[Dict[str, Any]] = []
        for e in expanded:
            path = e["path"]
            params = extract_params(path)
            is_dyn = is_dynamic_path(path)
            score = complexity_score(path)
            toks = path_tokens(path)
            # token mask: True for placeholder
            mask = tuple(1 if t == "{}" else 0 for t in toks)
            generic = tuple("{}" if t == "{}" else t for t in toks)
            routes.append(
                {
                    "method": e["method"],
                    "path": path,
                    "endpoint": e["endpoint"],
                    "source": e.get("source"),
                    "blueprint": e.get("blueprint"),
                    "order": e["order"],
                    "path_params": params,
                    "is_dynamic": bool(is_dyn),
                    "complexity_score": score,
                    "_norm": normalize_pattern(path),  # helper for internal use
                    "_tokens": toks,
                    "_mask": mask,
                    "_generic": generic,
                }
            )

        # Deterministic sort for routes: (path, method, order)
        # Tie-breakers: lexicographic path, then method, then registration order (ascending)
        routes.sort(key=lambda r: (r["path"], r["method"], r["order"]))
        _phase_ts['routes_sorted'] = time.perf_counter()

        # --- conflict detection (bucket by method then by token-length) ------------
        conflicts: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        by_method = defaultdict(list)
        for r in routes:
            by_method[r["method"]].append(r)

        # To keep O(n^2) worst-case but optimized: compare only routes with same token length
        buckets = defaultdict(list)
        for method, lst in by_method.items():
            for r in lst:
                key = (method, len(r["_tokens"]))
                buckets[key].append(r)

        # exact duplicates
        seen_exact = defaultdict(list)  # (method,path) -> list of routes
        for r in routes:
            seen_exact[(r["method"], r["path"])].append(r)
        for (method, path), group in sorted(seen_exact.items()):
            if len(group) > 1:
                involved = [
                    {"order": g["order"], "endpoint": g["endpoint"], "path": g["path"]}
                    for g in sorted(group, key=lambda x: x["order"])
                ]
                conflicts.append(
                    {
                        "method": method,
                        "path": path,
                        "severity": "critical",
                        "involved_routes": involved,
                        "resolution_suggestion": "Remove or merge duplicate route definitions; ensure unique (method,path).",
                    }
                )

        # Precompute positional indexes per bucket so they can be reused (reduces repeated work)
        bucket_indexes = {}
        # pattern and ambiguous conflicts (optimized)
        _pattern_checks = 0
        _candidate_intersections = 0
        for key, group in buckets.items():
            L = len(group)
            if L <= 1:
                continue
            # build or reuse positional indexes to cut down candidates
            if key in bucket_indexes:
                pos_index, placeholder_sets = bucket_indexes[key]
            else:
                pos_index = [defaultdict(set) for _ in range(len(group[0]["_tokens"]))]
                placeholder_sets = [set() for _ in range(len(group[0]["_tokens"]))]
                for idx, r in enumerate(group):
                    for p, tok in enumerate(r["_tokens"]):
                        if tok == "{}":
                            placeholder_sets[p].add(idx)
                        else:
                            pos_index[p][tok].add(idx)
                bucket_indexes[key] = (pos_index, placeholder_sets)

            # Heuristic: if bucket is very large and token-uniqueness is high, skip expensive pairwise
            LARGE_BUCKET = 300
            UNIQUE_TOKEN_THRESHOLD = 50
            unique_counts = [len(pos_index[p]) for p in range(len(pos_index))]
            if len(group) > LARGE_BUCKET and max(unique_counts) > UNIQUE_TOKEN_THRESHOLD:
                # quick detection for identical generic signatures only
                gen_map = defaultdict(list)
                for idx, r in enumerate(group):
                    gen_map[r["_generic"]].append(idx)
                for sig, idxs in gen_map.items():
                    if len(idxs) > 1:
                        for i in range(len(idxs)):
                            for j in range(i + 1, len(idxs)):
                                a = group[idxs[i]]
                                b = group[idxs[j]]
                                if a["path"] == b["path"] and a["method"] == b["method"]:
                                    continue
                                conflicts.append(
                                    {
                                        "method": a["method"],
                                        "path": a["_norm"],
                                        "severity": "error",
                                        "involved_routes": [
                                            {"order": a["order"], "endpoint": a["endpoint"], "path": a["path"]},
                                            {"order": b["order"], "endpoint": b["endpoint"], "path": b["path"]},
                                        ],
                                        "resolution_suggestion": "Make patterns more specific or rename parameters to avoid ambiguity.",
                                    }
                                )
                # skip the full pairwise index-based checks for this bucket
                continue

            handled_pairs = set()
            for i, a in enumerate(group):
                # candidate indices: intersection across positions of (same token OR placeholder)
                cand = None
                for p, tok in enumerate(a["_tokens"]):
                    _candidate_intersections += 1
                    s = set()
                    s.update(placeholder_sets[p])
                    s.update(pos_index[p].get(tok, set()))
                    if cand is None:
                        cand = s
                    else:
                        cand &= s
                    if not cand:
                        break
                if not cand:
                    continue
                for j in sorted(cand):
                    if j <= i:
                        continue
                    if (i, j) in handled_pairs:
                        continue
                    b = group[j]
                    if a["path"] == b["path"] and a["method"] == b["method"]:
                        continue
                    # now do exact pattern check (fast)
                    if pattern_conflict(a["path"], b["path"]):
                        _pattern_checks += 1
                        handled_pairs.add((i, j))
                        ta = a["_tokens"]
                        tb = b["_tokens"]
                        dynamic_mismatch = False
                        exact_mismatch = False
                        for xa, xb in zip(ta, tb):
                            if xa == xb:
                                continue
                            if xa == "{}" and xb == "{}":
                                dynamic_mismatch = True
                            elif xa == "{}" or xb == "{}":
                                exact_mismatch = True
                        sev = "warning" if (dynamic_mismatch and not exact_mismatch) else "error"
                        involved = [
                            {"order": a["order"], "endpoint": a["endpoint"], "path": a["path"]},
                            {"order": b["order"], "endpoint": b["endpoint"], "path": b["path"]},
                        ]
                        suggestion = (
                            "Reorder routes or make patterns more specific (use static segments or regex)"
                        )
                        conflicts.append(
                            {
                                "method": a["method"],
                                "path": a["_norm"],
                                "severity": sev,
                                "involved_routes": involved,
                                "resolution_suggestion": suggestion,
                            }
                        )

        # --- warnings ---------------------------------------------------------------
        # similar paths (possible typos) - compare each path to a small set of lexicographic neighbors
        # This reduces O(n^2) to O(n*k) where k is small (5) while still finding likely typos.
        neighbor_k = 5
        sim_buckets = defaultdict(list)
        for r in routes:
            # bucket by first literal segment (if any) and segment count
            toks = r["_tokens"]
            first_literal = next((t for t in toks if t != "{}"), r["path"][:3])
            key = (first_literal, len(toks))
            sim_buckets[key].append(r["path"])

        for key, lst in sim_buckets.items():
            lst = sorted(set(lst))
            L = len(lst)
            for i, a in enumerate(lst):
                # only compare with a few neighbors (likely to be similar when sorted)
                for j in range(i + 1, min(i + 1 + neighbor_k, L)):
                    b = lst[j]
                    if abs(len(a) - len(b)) > 3:
                        continue
                    dist = levenshtein_threshold(a, b, thresh=2)
                    if dist <= 2:
                        warnings.append(
                            {
                                "type": "similar_path",
                                "paths": [a, b],
                                "levenshtein": dist,
                                "suggestion": "Did you mean to use the same path? Check for typos or inconsistent pluralization.",
                            }
                        )

        # unreachable detection: use bucketed positional indexes to avoid O(n^2)
        for key, group in buckets.items():
            if len(group) <= 1:
                continue
            # build positional indexes (reuse approach from conflict detection)
            pos_index = [defaultdict(set) for _ in range(len(group[0]["_tokens"]))]
            placeholder_sets = [set() for _ in range(len(group[0]["_tokens"]))]
            for idx, r in enumerate(group):
                for p, tok in enumerate(r["_tokens"]):
                    if tok == "{}":
                        placeholder_sets[p].add(idx)
                    else:
                        pos_index[p][tok].add(idx)
            # for each route, find earlier candidate routes that could shadow it
            for idx_later, later in enumerate(group):
                # build candidate set
                cand = None
                for p, tok in enumerate(later["_tokens"]):
                    s = set()
                    s.update(placeholder_sets[p])
                    s.update(pos_index[p].get(tok, set()))
                    if cand is None:
                        cand = s
                    else:
                        cand &= s
                    if not cand:
                        break
                if not cand:
                    continue
                # check if any candidate has an earlier registration order
                shadow = None
                for ci in cand:
                    if ci == idx_later:
                        continue
                    candidate = group[ci]
                    if candidate["order"] < later["order"]:
                        # ensure candidate is actually broader (has at least one placeholder where later is static)
                        broader = False
                        for xa, xb in zip(candidate["_tokens"], later["_tokens"]):
                            if xa == "{}" and xb != "{}":
                                broader = True
                                break
                        if broader:
                            shadow = candidate
                            break
                if shadow:
                    warnings.append(
                        {
                            "type": "unreachable_route",
                            "route": later["path"],
                            "shadowed_by": shadow["path"],
                            "suggestion": "Register the specific (static) route before the broader dynamic route or make patterns mutually exclusive.",
                        }
                    )

        # missing source attribution (production scenario)
        for r in routes:
            if r.get("source") is None:
                warnings.append(
                    {
                        "type": "missing_source",
                        "route": r["path"],
                        "method": r["method"],
                        "suggestion": "Add source attribution (source=<filename>) for observability in production.",
                    }
                )

        # de-duplicate warnings deterministically
        def _warn_key(w):
            if "paths" in w:
                return (w["type"], tuple(sorted(w["paths"])), w.get("levenshtein", 0))
            return (w.get("type"), w.get("route"), w.get("shadowed_by"))

        uniq_warn = {(_warn_key(w)): w for w in warnings}
        warnings = list(uniq_warn.values())
        warnings.sort(key=lambda w: (_warn_key(w)))

        # --- pattern analysis ------------------------------------------------------
        total_dynamic = sum(1 for r in routes if r["is_dynamic"])
        most_complex = sorted(routes, key=lambda r: (-r["complexity_score"], r["order"]))[:5]
        avg_by_bp = {}
        bp_groups = defaultdict(list)
        for r in routes:
            bp_groups[r.get("blueprint")].append(r["complexity_score"])
        for bp, vals in bp_groups.items():
            avg_by_bp[bp or "<root>"] = round(sum(vals) / len(vals), 3)

        # potential bottlenecks: routes that have many pattern matches (collision count)
        potential_bottlenecks = []
        # estimate collision counts using bucketed positional index (cheap)
        for key, group in buckets.items():
            if len(group) <= 1:
                continue
            # build positional index
            pos_index = [defaultdict(set) for _ in range(len(group[0]["_tokens"]))]
            placeholder_sets = [set() for _ in range(len(group[0]["_tokens"]))]
            for idx, r in enumerate(group):
                for p, tok in enumerate(r["_tokens"]):
                    if tok == "{}":
                        placeholder_sets[p].add(idx)
                    else:
                        pos_index[p][tok].add(idx)
            for idx, r in enumerate(group):
                cand = None
                for p, tok in enumerate(r["_tokens"]):
                    s = set()
                    s.update(placeholder_sets[p])
                    s.update(pos_index[p].get(tok, set()))
                    if cand is None:
                        cand = s
                    else:
                        cand &= s
                    if not cand:
                        break
                cnt = (len(cand) - 1) if cand else 0
                if cnt >= 5:
                    potential_bottlenecks.append({"path": r["path"], "method": r["method"], "collision_count": cnt})
        potential_bottlenecks.sort(key=lambda x: (-x["collision_count"], x["path"]))

        pattern_analysis = {
            "most_complex_routes": [
                {"path": r["path"], "method": r["method"], "complexity_score": r["complexity_score"], "order": r["order"]}
                for r in most_complex
            ],
            "avg_complexity_by_blueprint": dict(sorted(avg_by_bp.items())),
            "total_dynamic_routes": total_dynamic,
            "potential_bottlenecks": potential_bottlenecks,
        }

        # --- summary ----------------------------------------------------------------
        # conflict severity distribution
        dist = defaultdict(int)
        for c in conflicts:
            dist[c["severity"]] += 1
        exec_ms = (time.perf_counter() - start) * 1000.0
        summary = {
            "total_routes": len(routes),
            "total_conflicts": len(conflicts),
            "total_warnings": len(warnings),
            "conflict_severity_distribution": dict(sorted(dist.items(), key=lambda x: x[0])),
            "execution_time_ms": round(exec_ms, 3),
        }

        # --- sanitize route entries for JSON output --------------------------------
        out_routes = []
        for r in routes:
            entry = {k: v for k, v in r.items() if not k.startswith("_")}
            out_routes.append(entry)

        # deterministic sort of conflicts
        def _conflict_key(c):
            return (severity_rank.get(c.get("severity", "info")), c.get("method", ""), c.get("path", ""), c.get("involved_routes", [{}])[0].get("order", 0))

        conflicts.sort(key=_conflict_key)
        _phase_ts['conflicts_done'] = time.perf_counter()

        _phase_ts['pattern_analysis_done'] = time.perf_counter()

        # include optional phase timings when debugging environment enabled
        phase_timings = None
        try:
            import os
            if os.environ.get('MINIAPP_PROFILE'):
                phase_timings = {k: round((v - start) * 1000.0, 3) for k, v in _phase_ts.items()}
                phase_timings.update({
                    "pattern_checks": _pattern_checks,
                    "candidate_intersections": _candidate_intersections,
                })
        except Exception:
            phase_timings = None

        manifest = {
            "routes": out_routes,
            "conflicts": conflicts,
            "warnings": warnings,
            "pattern_analysis": pattern_analysis,
            "summary": summary,
        }
        if phase_timings:
            manifest['summary']['phase_timings_ms'] = phase_timings

        return manifest

