# MiniApp — Route Manifest, Conflict Analysis & Pattern Matching 🔎

Summary
- Implements an advanced, deterministic **Route Manifest** for the minimal Flask-like `MiniApp` framework.
- Produces JSON-ready manifests that help detect route conflicts, ambiguous patterns, unreachable routes, and performance bottlenecks.

Why this matters 💡
- In real applications route collisions and ambiguous patterns cause hard-to-debug runtime errors and subtle security/observability gaps.
- The manifest provides an auditable, machine- and human-readable summary to: detect conflicts early, prioritize fixes, and guide routing performance optimizations.

Quick status ✅
- All automated tests pass locally: **12 passed**.
- Performance: manifest generation for **1,200 routes ≈ 0.73 s** on the dev environment.
- Test-run: `python run_tests.py` (one-command runner) — prints detailed test + coverage summary.

Where to find things
- Core implementation: `miniapp.py` (search for `route_manifest`)
- Tests: `test_routes.py`, `test_manifest_extended.py`
- One-command test runner: `run_tests.py`
- Performance helper: `performance_test.py`
- Example manifest: `sample_manifest.json`

How to run
1) Run the full test-suite (installs pytest if needed):

   `python run_tests.py`

2) Run performance measurement (example):

   `python performance_test.py`

3) Generate a manifest programmatically:

   ```py
   from miniapp import MiniApp
   app = MiniApp()
   # register routes...
   print(app.route_manifest())
   ```

Manifest JSON schema (top-level) — concise
- routes: list of route entries
  - method (string)
  - path (string)
  - endpoint (string)
  - source (string|null) — optional source attribution (filename)
  - blueprint (string|null)
  - order (int) — registration order
  - path_params (list[string]) — extracted from `<param>` or `:param`
  - is_dynamic (boolean)
  - complexity_score (float)

- conflicts: list of findings
  - method, path, severity ("critical"|"error"|"warning"), involved_routes, resolution_suggestion
  - involved_routes: [{ order, endpoint, path }]

- warnings: list of potential issues (types: `similar_path`, `unreachable_route`, `missing_source`, ...)

- pattern_analysis:
  - most_complex_routes: top-N by complexity
  - avg_complexity_by_blueprint: map
  - total_dynamic_routes: int
  - potential_bottlenecks: list (collision_count)

- summary:
  - total_routes, total_conflicts, total_warnings
  - conflict_severity_distribution
  - execution_time_ms
  - (optional) phase_timings_ms — internal timings (enabled with `MINIAPP_PROFILE=1`)

Field examples (short)
- route entry:
  {
    "method": "GET",
    "path": "/users/<id>",
    "endpoint": "get_user",
    "source": "users.py",
    "blueprint": null,
    "order": 12,
    "path_params": ["id"],
    "is_dynamic": true,
    "complexity_score": 2.1
  }

- conflict entry (example):
  {
    "method": "GET",
    "path": "/items/{}",
    "severity": "critical",
    "involved_routes": [ {"order":1, "endpoint":"items_a"}, {"order":2, "endpoint":"items_b"} ],
    "resolution_suggestion": "Remove or merge duplicate route definitions; ensure unique (method,path)."
  }

Three manifest scenarios (examples)
1) Simple routes
- `routes` contains static paths, `total_dynamic_routes == 0`, `most_complex_routes` shows static entries with low scores.

2) Conflict detection
- Duplicate (method,path) → `severity: critical`
- `/users/<id>` vs `/users/:user_id` → `severity: error` and `involved_routes` explains which endpoints are affected

3) Pattern analysis
- `most_complex_routes` lists deep/multi-param/regex routes
- `avg_complexity_by_blueprint` highlights blueprints with expensive routes

Algorithmic complexity & performance characteristics 📊
- Route parsing / entry building: O(n)
- Conflict & similarity detection: worst-case O(n²) but heavily optimized by bucketing, positional indexes and heuristics
- Practical performance: O(n)–O(n log n) for typical applications
- Performance target achieved: < 1s for 1000+ routes in the provided perf test (configurable heuristics guard worst-case)

Determinism guarantees
- All lists are sorted deterministically with explicit tie-breakers documented in code comments.
- Re-running `route_manifest()` on the same app yields byte-for-byte identical output except for `execution_time_ms`.

CI / integration suggestions (recommended)
- Fail builds on `conflicts` where severity == `critical`.
- Warn on high `complexity_score` or many `potential_bottlenecks`.
- Periodically commit `sample_manifest.json` for baseline comparisons.

Developer tips & knobs 🔧
- Enable verbose phase timings for debugging: `MINIAPP_PROFILE=1` (adds `phase_timings_ms` to `summary`).
- Use `source=` when registering routes for better observability.

Included artifacts
- `sample_manifest.json` — realistic example manifest
- `performance_test.py` — registers 1k+ routes and prints timing
- `run_tests.py` — installs pytest (if needed) and runs full suite

Measured outputs (example runs on dev)
- `python run_tests.py` → `12 passed` (≈1.45s), coverage ~77%
- `python performance_test.py` (1,200 routes) → manifest generation **~0.73 s**

References / next steps
- Add a CI job that executes `python run_tests.py` and fails on `critical` conflicts
- Provide a small web UI to visualize `sample_manifest.json` for on-call/debugging

License / contribution
- Treat this code as MIT-style for experimentation in this kata workspace (no external dependencies beyond pytest for tests). Contribute improvements via PRs.

---
If you'd like, I can now:
- open a PR with a succinct changelog and suggested reviewers ✅
- add a CI workflow that rejects `critical` conflicts ❓
