# Route Manifest (MiniApp)

🔧 **Feature:** Advanced Route Manifest + Conflict Analysis + Pattern Matching

## What is a Route Manifest?
A Route Manifest is a structured JSON snapshot of all registered routes in an application. It helps developers discover:
- route definitions (path, method, endpoint)
- conflicts and ambiguous registrations
- potential runtime performance hotspots
- complexity of patterns and dynamic parameters

This project implements `MiniApp.route_manifest()` — a deterministic, production-ready manifest generator with conflict detection and pattern analysis.

## JSON Schema (top-level fields)
- routes: list of route entries
  - method (string)
  - path (string)
  - endpoint (string)
  - source (string|null)
  - blueprint (string|null)
  - order (int)
  - path_params (array[string])
  - is_dynamic (boolean)
  - complexity_score (float)

- conflicts: list of conflict objects
  - method (string)
  - path (string)
  - severity ("critical"|"error"|"warning")
  - involved_routes (list of {order:int, endpoint:str})
  - resolution_suggestion (string)

- warnings: list of warning objects
  - type (string) e.g. "similar_path", "unreachable", "missing_source"
  - message (string)
  - additional fields depending on type

- pattern_analysis: insights about patterns
  - most_complex_routes (top 5 route entries)
  - total_dynamic_routes (int)
  - avg_complexity_by_blueprint (map)
  - potential_bottlenecks (list)

- summary: aggregate counts and timing
  - total_routes, total_conflicts, total_warnings
  - conflict_severity_distribution
  - execution_time_ms

## Examples

1) Simple routes
```json
{ "routes": [{"method":"GET","path":"/health","endpoint":"health","source":"app.py","blueprint":null,"order":1,"path_params":[],"is_dynamic":false,"complexity_score":1.05}], "conflicts":[], "warnings":[], "pattern_analysis":{...}, "summary":{...} }
```

2) Conflict detection (exact and pattern)
```json
{ "conflicts": [ {"method":"GET","path":"/items","severity":"critical","involved_routes":[{"order":1,"endpoint":"items_a"},{"order":2,"endpoint":"items_b"}],"resolution_suggestion":"Remove duplicate registrations"} ] }
```

3) Pattern analysis
```json
{ "pattern_analysis": { "most_complex_routes": [{"path":"/complex/<id>/sub/<name>", "complexity_score":3.2}], "total_dynamic_routes": 3, "avg_complexity_by_blueprint": {"<root>":1.45} } }
```

## Algorithmic Complexity
- Building route list: O(n)
- Pairwise conflict/pattern checks: O(n^2) worst-case
- Overall: O(n^2) worst-case but optimized heuristics make it fast in practice

## Running tests
- Run the full test suite (includes performance test):
  - python run_tests.py

## Performance Test
- `performance_test.py` registers 1000 routes and prints manifest generation time.
- Expected: < 1 second on typical development hardware.

## Files added / changed
- `miniapp.py` — implemented `route_manifest()`
- `performance_test.py` — 1000-route benchmark
- `test_performance.py` — ensures manifest < 1s for 1000 routes
- `run_tests.py` — one-command test runner
- `sample_manifest.json` — example manifest snapshot

## Notes
- Deterministic sorting guarantees identical manifest output across runs.
- Tie-breakers prefer registration `order` when necessary.

