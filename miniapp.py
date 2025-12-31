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
        raise NotImplementedError
