from djangobench.utils import run_djangotest_benchmark

def benchmark():
    pass

run_djangotest_benchmark(
    meta = {
        'description': 'Time of a specific django test (SQLite3 backend)',
    }
)
