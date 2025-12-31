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
        """
        Generate comprehensive route manifest with conflict detection and pattern analysis.

        Algorithmic Complexity:
        - Building route entries: O(n)
        - Conflict and warnings detection: O(n^2) in worst case due to pairwise checks
        - Overall: O(n^2) worst-case but typical cases will be closer to O(n)

        Performance-note: Designed to run in under 1 second for 1000 routes on modern hardware.

        Returns:
            A JSON-serializable dict with keys: routes, conflicts, warnings, pattern_analysis, summary
        """
        import time
        from collections import defaultdict
        import math

        start = time.perf_counter()

        # Helper utilities
        def extract_params(path: str) -> List[str]:
            # support <param> and :param styles
            import re
            params = []
            params += re.findall(r"<([A-Za-z_][A-Za-z0-9_]*)>", path)
            params += re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", path)
            return params

        def canonical_pattern(path: str) -> str:
            # convert parameter placeholders to a canonical token {}
            import re
            p = re.sub(r"<([A-Za-z_][A-Za-z0-9_]*)>", "{}", path)
            p = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", "{}", p)
            return p

        def is_regex_like(path: str) -> bool:
            # crude heuristic for regex patterns
            return any(c in path for c in ['(', ')', '|', '?', '*', '+'])

        def complexity_score(path: str) -> float:
            params = extract_params(path)
            score = 1.0 + len(params)
            if is_regex_like(path):
                score += 3.0
            return float(score)

        def segments(path: str) -> List[str]:
            segs = [s for s in path.split('/') if s != '']
            return segs

        # Build route entries, expand any methods lists into separate logical entries
        entries: List[Dict[str, Any]] = []
        for r in sorted(self._routes, key=lambda x: x.order):  # stable ordering by registration
            methods = []
            if r.methods:
                methods = [m.upper() for m in r.methods]
            methods = [r.method] + [m for m in methods if m != r.method]
            for m in methods:
                params = extract_params(r.path)
                entry = {
                    'method': m,
                    'path': r.path,
                    'endpoint': r.endpoint,
                    'source': r.source,
                    'blueprint': r.blueprint,
                    'order': r.order,
                    'path_params': params,
                    'is_dynamic': len(params) > 0,
                    'complexity_score': complexity_score(r.path),
                    'canonical_pattern': canonical_pattern(r.path),
                }
                entries.append(entry)

        # Deterministic sort: primarily by order, tie-break by method then path
        entries.sort(key=lambda e: (e['order'], e['method'], e['path']))

        # Conflict detection
        conflicts: List[Dict[str, Any]] = []
        # exact duplicates: map (method,path) -> list
        by_method_path: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        for e in entries:
            by_method_path[(e['method'], e['path'])].append(e)
        for (method, path), lst in sorted(by_method_path.items(), key=lambda x: (x[0][0], x[0][1])):
            if len(lst) > 1:
                conflict = {
                    'method': method,
                    'path': path,
                    'severity': 'critical',
                    'involved_routes': [{'order': r['order'], 'endpoint': r['endpoint']} for r in lst],
                    'resolution_suggestion': 'Remove or namespace duplicate route patterns or consolidate handlers.'
                }
                conflicts.append(conflict)

        # pattern conflicts: same canonical pattern but different literal path or different param naming
        by_pattern: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in entries:
            by_pattern[e['canonical_pattern']].append(e)
        for pattern, lst in sorted(by_pattern.items(), key=lambda x: x[0]):
            # if multiple distinct literal paths map to same pattern, and not already exact duplicate
            literal_paths = set(r['path'] for r in lst)
            methods = set(r['method'] for r in lst)
            if len(literal_paths) > 1:
                # for each method group, if multiple entries for same method across different paths
                grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
                for r in lst:
                    grouped[(r['method'], r['canonical_pattern'])].append(r)
                for (method, _), g in grouped.items():
                    literal_paths_in_g = set(r['path'] for r in g)
                    if len(literal_paths_in_g) > 1:
                        # If any exact conflict already recorded, skip marking extra
                        if not any(c for c in conflicts if c['method'] == method and c['path'] in literal_paths_in_g):
                            conflict = {
                                'method': method,
                                'path': pattern,
                                'severity': 'error',
                                'involved_routes': [{'order': r['order'], 'endpoint': r['endpoint'], 'path': r['path']} for r in g],
                                'resolution_suggestion': 'Normalize parameter syntax or disambiguate routes with prefixes.'
                            }
                            conflicts.append(conflict)

        # ambiguous conflicts: same shape and same positions are dynamic and differ only by param name
        for pattern, lst in sorted(by_pattern.items(), key=lambda x: x[0]):
            if len(lst) < 2:
                continue
            # Skip expensive checks for extremely large groups (rare in practice)
            if len(lst) > 300:
                continue
            # group by literal segment signature length and static segments
            sig_map: Dict[Tuple[int, Tuple[Tuple[int, str], ...]], List[Dict[str, Any]]] = defaultdict(list)
            for r in lst:
                segs = segments(r['path'])
                # signature: length and for each index, static portion or 0 if dynamic
                sig = (len(segs), tuple((i, seg if ('<' not in seg and ':' not in seg) else '{}') for i, seg in enumerate(segs)))
                sig_map[sig].append(r)
            for sig, group in sig_map.items():
                if len(group) > 1:
                    # If they are not exact duplicates and not pattern conflicts already recorded
                    endpoints = [g['endpoint'] for g in group]
                    # Only warn when param names differ causing ambiguity
                    names = [tuple(g['path_params']) for g in group]
                    if len(set(names)) > 1:
                        # severity warning
                        conflict = {
                            'method': ','.join(sorted(set([g['method'] for g in group]))),
                            'path': pattern if pattern else group[0]['path'],
                            'severity': 'warning',
                            'involved_routes': [{'order': r['order'], 'endpoint': r['endpoint'], 'path': r['path']} for r in group],
                            'resolution_suggestion': 'Rename parameters or provide more specific static segments to avoid ambiguity.'
                        }
                        conflicts.append(conflict)

        # Warnings detection: similar paths (Levenshtein distance < 3) and unreachable routes & missing source
        warnings: List[Dict[str, Any]] = []

        # Bounded Levenshtein (early exit when distance > max_dist) to improve performance
        def bounded_levenshtein(a: str, b: str, max_dist: int = 2) -> int:
            if a == b:
                return 0
            la, lb = len(a), len(b)
            if abs(la - lb) > max_dist:
                return max_dist + 1
            # Ensure a is the shorter
            if la > lb:
                a, b = b, a
                la, lb = lb, la
            prev = list(range(lb + 1))
            for i in range(1, la + 1):
                cur = [i] + [0] * lb
                ai = a[i - 1]
                # We can restrict j window to [i-max_dist, i+max_dist]
                start = max(1, i - max_dist)
                end = min(lb, i + max_dist)
                for j in range(start, end + 1):
                    cost = 0 if ai == b[j - 1] else 1
                    left = prev[j] + 1
                    down = cur[j - 1] + 1
                    diag = prev[j - 1] + cost
                    cur[j] = min(left, down, diag)
                # If all values in cur within window are > max_dist, bail
                if min(cur[start:end + 1]) > max_dist:
                    return max_dist + 1
                prev = cur
            res = prev[lb]
            return res

        # Build buckets by simple prefix to avoid O(n^2) all-pairs
        path_list = [e['path'] for e in entries]
        prefix_buckets: Dict[str, List[str]] = defaultdict(list)
        for p in path_list:
            parts = p.split('/')
            key = parts[1] if len(parts) > 1 and parts[1] else parts[0]
            prefix_buckets[key].append(p)

        for key, p_list in prefix_buckets.items():
            ln = len(p_list)
            # Precompute n-gram signatures for quick filtering (deterministic)
            grams = {}
            ngram = 4
            for p in p_list:
                s = p
                g = set()
                L = max(len(s) - ngram + 1, 1)
                for i in range(L):
                    g.add(s[i:i+ngram])
                grams[p] = g

            # If bucket is very large, limit expensive pairwise checks by deterministic sampling
            max_pairs = 2000
            pair_count = 0
            max_items = 400
            if ln > max_items:
                p_list = p_list[:max_items]
                ln = len(p_list)

            for i in range(ln):
                a = p_list[i]
                for j in range(i + 1, ln):
                    b = p_list[j]
                    if abs(len(a) - len(b)) > 3:
                        continue
                    # quick n-gram filter
                    if grams[a].isdisjoint(grams[b]):
                        continue
                    d = bounded_levenshtein(a, b, max_dist=2)
                    if d <= 2:
                        warnings.append({'type': 'similar_paths', 'paths': (a, b), 'distance': d, 'suggestion': 'Check for typos or consolidate routes.'})
                    pair_count += 1
                    if pair_count > max_pairs:
                        break
                if pair_count > max_pairs:
                    break

        # Unreachable routes: index earlier routes by segment count for quick lookup
        by_length: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for e in entries:
            by_length[len(segments(e['path']))].append(e)

        for later in entries:
            later_segs = segments(later['path'])
            candidates = by_length.get(len(later_segs), [])
            for earlier in candidates:
                if earlier['order'] >= later['order']:
                    continue
                earlier_segs = segments(earlier['path'])
                shadow = True
                for es, ls in zip(earlier_segs, later_segs):
                    es_dynamic = ('<' in es) or (':' in es)
                    if es_dynamic:
                        # earlier dynamic can match later static
                        continue
                    if es != ls:
                        shadow = False
                        break
                if shadow:
                    warnings.append({'type': 'unreachable_route', 'shadowed_route': later['path'], 'by': earlier['path'], 'suggestion': 'Place specific static routes before general dynamic ones.'})
                    break

        # Missing source attribution
        for e in entries:
            if not e.get('source'):
                warnings.append({'type': 'missing_source', 'path': e['path'], 'suggestion': 'Add source attribution for easier debugging.'})

        # Pattern analysis
        total_dynamic = sum(1 for e in entries if e['is_dynamic'])
        most_complex = sorted(entries, key=lambda e: (-e['complexity_score'], e['order'], e['path']))[:5]
        avg_by_bp: Dict[Optional[str], float] = {}
        by_bp: Dict[Optional[str], List[float]] = defaultdict(list)
        for e in entries:
            by_bp[e['blueprint']].append(e['complexity_score'])
        for bp, scores in by_bp.items():
            avg_by_bp[bp if bp is not None else 'default'] = sum(scores) / len(scores) if scores else 0.0

        # potential bottlenecks: heuristics - complexity > 4 or many similar patterns
        pattern_counts: Dict[str, int] = {pat: len(lst) for pat, lst in by_pattern.items()}
        potential_bottlenecks = []
        for e in entries:
            reasons = []
            if e['complexity_score'] > 4.0:
                reasons.append('high_complexity')
            if pattern_counts.get(e['canonical_pattern'], 0) > 1:
                reasons.append('pattern_collision')
            if reasons:
                potential_bottlenecks.append({'method': e['method'], 'path': e['path'], 'reasons': reasons, 'complexity_score': e['complexity_score']})

        # Build final structures removing internal-only fields
        route_list = []
        for e in entries:
            r = {k: v for k, v in e.items() if k != 'canonical_pattern'}
            route_list.append(r)

        # Deterministic sorting of conflicts and warnings
        severity_rank = {'critical': 0, 'error': 1, 'warning': 2}
        conflicts.sort(key=lambda c: (severity_rank.get(c.get('severity'), 99), c.get('method', ''), c.get('path', '')))
        warnings.sort(key=lambda w: (w.get('type', ''), str(w.get('paths', w.get('path', w.get('shadowed_route', ''))))))

        # Summary
        exec_time = (time.perf_counter() - start) * 1000.0
        summary = {
            'total_routes': len(route_list),
            'total_conflicts': len(conflicts),
            'total_warnings': len(warnings),
            'conflict_severity_distribution': {
                'critical': sum(1 for c in conflicts if c['severity'] == 'critical'),
                'error': sum(1 for c in conflicts if c['severity'] == 'error'),
                'warning': sum(1 for c in conflicts if c['severity'] == 'warning'),
            },
            'execution_time_ms': exec_time,
        }

        manifest = {
            'routes': route_list,
            'conflicts': conflicts,
            'warnings': warnings,
            'pattern_analysis': {
                'most_complex_routes': [{'path': r['path'], 'method': r['method'], 'complexity_score': r['complexity_score'], 'order': r['order']} for r in most_complex],
                'avg_complexity_by_blueprint': avg_by_bp,
                'total_dynamic_routes': total_dynamic,
                'potential_bottlenecks': potential_bottlenecks,
            },
            'summary': summary,
        }

        return manifest

