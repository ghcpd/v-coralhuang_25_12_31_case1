from miniapp import MiniApp
import pytest


def test_conflict_severity_levels():
    app = MiniApp()

    @app.route('/a', method='GET')
    def a1():
        return 1

    @app.route('/a', method='GET')
    def a2():
        return 2

    @app.route('/users/<id>', method='GET')
    def u1():
        return 1

    @app.route('/users/:user_id', method='GET')
    def u2():
        return 2

    manifest = app.route_manifest()
    severities = {c['severity'] for c in manifest['conflicts']}
    assert 'critical' in severities
    assert 'error' in severities


def test_performance_manifest_under_threshold():
    import subprocess, sys, re
    rc = subprocess.call([sys.executable, 'performance_test.py'])
    assert rc == 0, 'Performance test exceeded threshold (<1000ms)'
