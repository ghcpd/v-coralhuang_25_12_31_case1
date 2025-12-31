#!/usr/bin/env python3
"""Generate sample manifests for README."""

from miniapp import MiniApp
import json

# Sample 1: Simple app with basic routes
app1 = MiniApp('simple_app')

@app1.route('/health', method='GET', source='app.py')
def health():
    return 'ok'

@app1.route('/status', method='GET', source='app.py')
def status():
    return 'running'

@app1.route('/api/users/<user_id>', method='GET', source='api.py')
def get_user():
    return 'user'

manifest1 = app1.route_manifest()
with open('sample_simple_manifest.json', 'w') as f:
    json.dump(manifest1, f, indent=2)

# Sample 2: App with conflicts
app2 = MiniApp('conflict_app')

# Exact conflict
@app2.route('/data', method='GET', source='v1.py', endpoint='get_data_v1')
def get_data_v1():
    return 'data'

@app2.route('/data', method='GET', source='v2.py', endpoint='get_data_v2')
def get_data_v2():
    return 'data'

# Pattern/Ambiguous conflict
@app2.route('/items/<id>', method='GET', source='items.py')
def get_item():
    return 'item'

@app2.route('/items/<name>', method='GET', source='items_alt.py')
def get_item_alt():
    return 'item'

manifest2 = app2.route_manifest()
with open('sample_conflicts_manifest.json', 'w') as f:
    json.dump(manifest2, f, indent=2)

print("Samples generated:")
print(f"  - sample_simple_manifest.json")
print(f"  - sample_conflicts_manifest.json")
print(f"\nConflicts found: {len(manifest2['conflicts'])}")
for c in manifest2['conflicts']:
    print(f"  - {c['type']}: {c['method']} {c['severity']}")
