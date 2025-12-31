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


class Blueprint:
    def __init__(self, name: str):
        self.name = name
        self._routes: List[Tuple[str, str, Handler, Optional[str], str]] = []
        # tuple: (method, path, handler, source, endpoint)

    def route(self, path: str, method: str = "GET", source: Optional[str] = None, endpoint: Optional[str] = None):
        def decorator(fn: Handler):
            ep = endpoint or fn.__name__
            self._routes.append((method.upper(), path, fn, source, ep))
            return fn
        return decorator


class MiniApp:
    def __init__(self, name: str = "app"):
        self.name = name
        self._routes: List[Route] = []
        self._counter = 0  # registration order

    def route(self, path: str, method: str = "GET", source: Optional[str] = None, endpoint: Optional[str] = None):
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
                )
            )
            return fn
        return decorator

    def register_blueprint(self, bp: Blueprint, url_prefix: str = ""):
        for method, path, fn, source, endpoint in bp._routes:
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
                )
            )

    # =======================
    # NEW FEATURE (TODO)
    # =======================
    def route_manifest(self) -> Dict[str, Any]:
        """
        TODO: Implement Route Manifest.

        Expected high-level behavior:
        - Return a dict that is JSON-serializable.
        - Include:
            * routes: list of route entries (one per registered route)
            * conflicts: list of detected conflicts/overrides
            * summary: aggregate counts
        - Stable/deterministic ordering.
        """
        raise NotImplementedError
