# MiniApp Route Manifest Feature

## Overview

The Route Manifest is a comprehensive analysis tool for MiniApp's routing system that provides developers with deep insights into their application's route configuration. It solves real-world problems such as:

- **Route Conflicts Detection**: Identifies duplicate routes, ambiguous patterns, and potential runtime errors before deployment
- **Performance Analysis**: Highlights complex route patterns that may impact request routing performance
- **Maintenance Insights**: Reveals similar paths that might be typos, unreachable routes, and missing documentation
- **Debugging Aid**: Provides structured data for troubleshooting routing issues in development and production

## JSON Schema

The `route_manifest()` method returns a JSON-serializable dictionary with the following structure:

```json
{
  "routes": [
    {
      "method": "string",           // HTTP method (GET, POST, etc.)
      "path": "string",             // Route path pattern
      "endpoint": "string",         // Endpoint name
      "source": "string|null",      // Source file attribution
      "blueprint": "string|null",   // Blueprint name
      "order": "integer",           // Registration order
      "path_params": ["string"],    // Extracted parameter names
      "is_dynamic": "boolean",      // Whether route contains parameters
      "complexity_score": "float"   // Route complexity metric
    }
  ],
  "conflicts": [
    {
      "method": "string",
      "path": "string",
      "severity": "string",         // "critical" | "error" | "warning"
      "involved_routes": [
        {
          "order": "integer",
          "endpoint": "string"
        }
      ],
      "resolution_suggestion": "string"
    }
  ],
  "warnings": [
    {
      "type": "string",             // "similar_paths" | "missing_source"
      "message": "string",
      "involved_routes": [...],
      "suggestion": "string"
    }
  ],
  "pattern_analysis": {
    "most_complex_routes": [...],   // Top 5 routes by complexity
    "avg_complexity_by_blueprint": {"blueprint": "float"},
    "total_dynamic_routes": "integer",
    "potential_bottlenecks": [...]  // Routes with high complexity
  },
  "summary": {
    "total_routes": "integer",
    "total_conflicts": "integer",
    "total_warnings": "integer",
    "conflict_severity_distribution": {"severity": "count"},
    "execution_time_ms": "float"
  }
}
```

## Example Outputs

### Simple Routes

```json
{
  "routes": [
    {
      "method": "GET",
      "path": "/health",
      "endpoint": "health",
      "source": "app.py",
      "blueprint": null,
      "order": 1,
      "path_params": [],
      "is_dynamic": false,
      "complexity_score": 1.0
    }
  ],
  "conflicts": [],
  "warnings": [],
  "pattern_analysis": {
    "most_complex_routes": [...],
    "avg_complexity_by_blueprint": {"main": 1.0},
    "total_dynamic_routes": 0,
    "potential_bottlenecks": []
  },
  "summary": {
    "total_routes": 1,
    "total_conflicts": 0,
    "total_warnings": 0,
    "conflict_severity_distribution": {},
    "execution_time_ms": 0.1
  }
}
```

### Conflict Detection

```json
{
  "conflicts": [
    {
      "method": "GET",
      "path": "/conflict",
      "severity": "critical",
      "involved_routes": [
        {"order": 6, "endpoint": "conflict_a"},
        {"order": 7, "endpoint": "conflict_b"}
      ],
      "resolution_suggestion": "Remove duplicate routes or merge handlers"
    }
  ]
}
```

### Pattern Analysis Results

```json
{
  "pattern_analysis": {
    "most_complex_routes": [
      {
        "method": "GET",
        "path": "/api/<version>/users/<user_id>/posts/<post_id>/comments",
        "complexity_score": 4.0
      }
    ],
    "avg_complexity_by_blueprint": {
      "api": 2.5,
      "main": 1.8
    },
    "total_dynamic_routes": 15,
    "potential_bottlenecks": [
      {
        "method": "GET",
        "path": "/complex/<id>/sub/<name>",
        "complexity_score": 3.0
      }
    ]
  }
}
```

## Algorithmic Complexity

- **Time Complexity**: O(n²) in worst case for conflict and warning detection, but optimized for typical use cases
- **Space Complexity**: O(n) for route storage and analysis
- **Performance Target**: < 1 second for 1000 routes, < 10ms for 100 routes
- **Optimizations**: Early termination for similarity checks, conditional expensive operations for large route sets

## Test Script

The `run_tests.py` script provides automated testing with the following features:

- Installs pytest and coverage tools if needed
- Runs the complete test suite
- Provides detailed pass/fail breakdown
- Shows execution time and coverage percentage
- Exits with non-zero code on failures

Usage:
```bash
python run_tests.py
```

Or on Unix-like systems:
```bash
./run_tests.py
```

## Performance Test

The `performance_test.py` script validates performance requirements:

- Registers 1000+ routes with various patterns
- Measures manifest generation time
- Ensures completion in < 1 second
- Reports detailed statistics

Run with:
```bash
python performance_test.py
```

## Implementation Details

- **Deterministic Output**: All lists are sorted stably to ensure identical output for identical input
- **Parameter Extraction**: Supports both `<param>` and `:param` syntax
- **Complexity Scoring**: Static routes = 1.0, single param = 2.0, multiple params = 3.0+
- **Conflict Types**: Critical (exact duplicates), Error (pattern conflicts), Warning (ambiguous)
- **Warning Types**: Similar paths (Levenshtein < 3), missing source attribution

## Usage in Production

```python
from miniapp import MiniApp

app = MiniApp()

# Register routes...

# Generate manifest for analysis
manifest = app.route_manifest()

# Check for critical issues
if manifest["summary"]["conflict_severity_distribution"].get("critical", 0) > 0:
    print("Critical route conflicts detected!")

# Analyze complexity
avg_complexity = sum(r["complexity_score"] for r in manifest["routes"]) / len(manifest["routes"])
if avg_complexity > 2.0:
    print("High route complexity detected")
```

This feature provides production-ready route analysis capabilities essential for maintaining large Flask-like applications.