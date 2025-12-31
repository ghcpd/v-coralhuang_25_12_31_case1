import cProfile, pstats, io
from performance_test import build_app

app = build_app(1200)
pr = cProfile.Profile()
pr.enable()
app.route_manifest()
pr.disable()
s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumtime')
ps.print_stats(40)
print(s.getvalue())
