# MiniApp Route Manifest

🔧 **Feature**: Advanced Route Manifest + Conflict Analysis + Pattern Matching

## What is a Route Manifest?
A Route Manifest is a structured JSON document that catalogs all registered routes in a MiniApp application and provides automated analysis: conflict detection, warnings for problematic patterns, and per-route complexity metrics. It helps teams discover duplicated or ambiguous routes, identify unreachable endpoints, and find potential performance bottlenecks in the routing table.

## JSON Schema (summary)
Top-level object keys:
- `routes` (list): each entry:
  - `method` (str)
  - `path` (str)
  - `endpoint` (str)
  - `source` (str|null)
  - `blueprint` (str|null)
  - `order` (int)
  - `path_params` (list[str])
  - `is_dynamic` (bool)
  - `complexity_score` (float)

- `conflicts` (list): each entry:
  - `method` (str)
  - `path` (str)
  - `severity` ("critical"|"error"|"warning")
  - `involved_routes` (list of `{order:int, endpoint:str, path?:str}`)
  - `resolution_suggestion` (str)

- `warnings` (list): diagnostic warnings e.g. `similar_paths`, `unreachable_route`, `missing_source` with relevant fields

- `pattern_analysis` (object):
  - `most_complex_routes` (top 5 list)
  - `avg_complexity_by_blueprint` (map blueprint -> avg_score)
  - `total_dynamic_routes` (int)
  - `potential_bottlenecks` (list)

- `summary` (object): totals, severity distribution, and `execution_time_ms` (float)

## Example manifest snippets

1) Simple routes
```json
{
  "routes": [
    {"method":"GET","path":"/health","endpoint":"health","source":"app.py","blueprint":null,"order":1,"path_params":[],"is_dynamic":false,"complexity_score":1.0}
  ]
}
```

2) Conflict detection (critical and error)
```json
{
  "conflicts": [
    {"method":"GET","path":"/items","severity":"critical","involved_routes":[{"order":1,"endpoint":"items_a"},{"order":2,"endpoint":"items_b"}]},
    {"method":"GET","path":"/users/{}/profile","severity":"error","involved_routes":[{"order":3,"endpoint":"u1","path":"/users/<id>/profile"},{"order":4,"endpoint":"u2","path":"/users/:id/profile"}]}
  ]
}
```

3) Pattern analysis results
```json
{
  "pattern_analysis": {
    "most_complex_routes": [{"path":"/x/(re).*","method":"GET","complexity_score":5.0,"order":10}],
    "avg_complexity_by_blueprint": {"default":1.25, "admin":2.0},
    "total_dynamic_routes": 12,
    "potential_bottlenecks": [{"method":"GET","path":"/search/(.*)","reasons":["high_complexity"]}]
  }
}
```

## Algorithmic Complexity
- Building entries: O(n)
- Pairwise pattern/conflict detection: O(n^2) worst-case
- Most operations use sorting / grouping for deterministic output

The implementation is optimized for typical workloads and completes the manifest generation for 1000 routes in under 1 second on modern hardware (see performance tests).

## Running tests
A convenience script is provided:

- Run: python run_tests.py

It will:
- install `pytest` and `pytest-cov` if missing
- run the unit tests
- run a performance test that registers 1200 routes and measures manifest generation time
- generate `sample_manifest.json`

## performance_test.py
This script registers 1200 mixed static/dynamic routes, runs `route_manifest()` and prints `manifest_time_ms` and writes `sample_manifest.json`.

## Notes and Design Decisions
- Parameter styles supported: `<param>` and `:param`.
- For conflict detection we define:
  - `critical` for exact (method, path) duplicates
  - `error` for equivalent patterns with different literal strings
  - `warning` for ambiguous parameter naming where registration order matters
- Deterministic ordering: routes are sorted by registration `order` then method then path. Conflicts are sorted by severity rank then method then path. This guarantees identical output across runs.

## Files added
- `performance_test.py` - performance measurement and sample manifest generation
- `run_tests.py` - one-command test runner
- `test_manifest_extra.py` - extra tests ensuring conflict severity and performance assertions
- `sample_manifest.json` - created by `performance_test.py` when run

## Contact
If you integrate this into a larger project, consider adding more sophisticated pattern-parser to support full regex and method-based resolution priority.
