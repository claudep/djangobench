import argparse
import inspect
import os

# timeit uses either time.time() or time.clock() depending on which is more
# accurate on the current platform:
from timeit import default_timer as time_f

try:
    import cProfile as profile
except ImportError:
    import profile

benchmark_parser = argparse.ArgumentParser()
benchmark_parser.add_argument('-t', '--trials', type=int, default=100)
benchmark_parser.add_argument('-p', '--param', default='')

def run_benchmark(benchmark, syncdb=True, setup=None, trials=None, handle_argv=True, meta={}):
    """
    Run a benchmark a few times and report the results.

    Arguments:

        benchmark
            The benchmark callable. ``run_benchmark`` will time
            the executation of this function and report those times
            back to the harness. However, if ``benchmark`` returns
            a value, that result will reported instead of the
            raw timing.

        syncdb
            If True, a syncdb will be performed before running
            the benchmark.

        setup
            A function to be called before running the benchmark
            function(s).

        trials
            The number of times to run the benchmark function. If not given
            and if ``handle_argv`` is ``True`` this'll be automatically
            determined from the ``--trials`` flag.

        handle_argv
            ``True`` if the script should handle ``sys.argv`` and set
            the number of trials accordingly.

        meta
            Key/value pairs to be returned as part of the benchmark results.
    """
    if handle_argv:
        args = benchmark_parser.parse_args()
        trials = trials or args.trials

    print_benchmark_header(benchmark, meta)

    if syncdb:
        from django.core.management import call_command
        call_command("syncdb", verbosity=0)

    if setup:
        setup()

    for x in xrange(trials):
        start = time_f()
        profile_file = os.environ.get('DJANGOBENCH_PROFILE_FILE', None)
        if profile_file is not None:
            loc = locals().copy()
            profile.runctx('benchmark_result = benchmark()', globals(), loc, profile_file)
            benchmark_result = loc['benchmark_result']
        else:
            benchmark_result = benchmark()
        if benchmark_result is not None:
            print benchmark_result
        else:
            print time_f() - start

def run_comparison_benchmark(benchmark_a, benchmark_b, syncdb=True, setup=None, trials=None, handle_argv=True, meta={}):
    """
    Benchmark the difference between two functions.

    Arguments are as for ``run_benchmark``, except that this takes 2
    benchmark functions, an A and a B, and reports the difference between
    them.

    For example, you could use this to test the overhead of an ORM query
    versus a raw SQL query -- pass the ORM query as ``benchmark_a`` and the
    raw query as ``benchmark_b`` and this function will report the
    difference in time between them.

    For best results, the A function should be the more expensive one
    (otherwise djangobench will report results like "-1.2x slower", which
    is just confusing).
    """
    if handle_argv:
        args = benchmark_parser.parse_args()
        trials = trials or args.trials

    print_benchmark_header(benchmark_a, meta)

    if syncdb:
        from django.core.management import call_command
        call_command("syncdb", verbosity=0)

    if setup:
        setup()

    for x in xrange(trials):
        start_a = time_f()
        result_a = benchmark_a()
        result_a = result_a or time_f() - start_a

        start_b = time_f()
        result_b = benchmark_b()
        result_b = result_b or time_f() - start_b

        print result_a - result_b

from django.test.simple import DjangoTestSuiteRunner

class BenchmarkTestSuiteRunner(DjangoTestSuiteRunner):
    # setup_for_benchmark and teardown_for_benchmark are separing the run_tests method in two steps
    def setup_for_benchmark(self, test_labels):
        self.setup_test_environment()
        suite = self.build_suite(test_labels, [])
        self.old_config = self.setup_databases()
        return suite

    def teardown_for_benchmark(self):
        self.teardown_databases(self.old_config)
        self.teardown_test_environment()

RUNTESTS_DIR = os.getcwd() #os.path.dirname(__file__)

# Copy of tests/runtests.py geodjango
def geodjango(settings):
    # All databases must have spatial backends to run GeoDjango tests.
    spatial_dbs = [name for name, db_dict in settings.DATABASES.items()
                   if db_dict['ENGINE'].startswith('django.contrib.gis')]
    return len(spatial_dbs) == len(settings.DATABASES)

# Copy of tests/runtests.py get_test_modules
def get_test_modules():
    from django import contrib
    CONTRIB_DIR_NAME = 'django.contrib'
    MODEL_TESTS_DIR_NAME = 'modeltests'
    REGRESSION_TESTS_DIR_NAME = 'regressiontests'
    CONTRIB_DIR = os.path.dirname(contrib.__file__)
    MODEL_TEST_DIR = os.path.join(RUNTESTS_DIR, MODEL_TESTS_DIR_NAME)
    REGRESSION_TEST_DIR = os.path.join(RUNTESTS_DIR, REGRESSION_TESTS_DIR_NAME)
    REGRESSION_SUBDIRS_TO_SKIP = ['locale']
    modules = []
    for loc, dirpath in (
        (MODEL_TESTS_DIR_NAME, MODEL_TEST_DIR),
        (REGRESSION_TESTS_DIR_NAME, REGRESSION_TEST_DIR),
        (CONTRIB_DIR_NAME, CONTRIB_DIR)):
        for f in os.listdir(dirpath):
            if (f.startswith('__init__') or
                f.startswith('.') or
                f.startswith('sql') or
                os.path.basename(f) in REGRESSION_SUBDIRS_TO_SKIP):
                continue
            modules.append((loc, f))
    return modules

# Copy of tests/runtests.py setup
def runtests_setup(verbosity, test_labels):
    import tempfile
    from django.conf import settings
    ALWAYS_INSTALLED_APPS = [
        'django.contrib.contenttypes',
        'django.contrib.auth',
        'django.contrib.sites',
        'django.contrib.flatpages',
        'django.contrib.redirects',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.comments',
        'django.contrib.admin',
        'django.contrib.admindocs',
        'django.contrib.databrowse',
        'django.contrib.staticfiles',
        'django.contrib.humanize',
        'regressiontests.staticfiles_tests',
        'regressiontests.staticfiles_tests.apps.test',
        'regressiontests.staticfiles_tests.apps.no_label',
    ]
    TEST_TEMPLATE_DIR = 'templates'
    TEMP_DIR = tempfile.mkdtemp(prefix='django_')

    state = {
        'INSTALLED_APPS': settings.INSTALLED_APPS,
        'ROOT_URLCONF': getattr(settings, "ROOT_URLCONF", ""),
        'TEMPLATE_DIRS': settings.TEMPLATE_DIRS,
        'USE_I18N': settings.USE_I18N,
        'LOGIN_URL': settings.LOGIN_URL,
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'MIDDLEWARE_CLASSES': settings.MIDDLEWARE_CLASSES,
        'STATIC_URL': settings.STATIC_URL,
        'STATIC_ROOT': settings.STATIC_ROOT,
    }

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.ROOT_URLCONF = 'urls'
    settings.STATIC_URL = '/static/'
    settings.STATIC_ROOT = os.path.join(TEMP_DIR, 'static')
    settings.TEMPLATE_DIRS = (os.path.join(RUNTESTS_DIR, TEST_TEMPLATE_DIR),)
    settings.USE_I18N = True
    settings.LANGUAGE_CODE = 'en'
    settings.LOGIN_URL = '/accounts/login/'
    settings.MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.common.CommonMiddleware',
    )
    settings.SITE_ID = 1
    # For testing comment-utils, we require the MANAGERS attribute
    # to be set, so that a test email is sent out which we catch
    # in our tests.
    settings.MANAGERS = ("admin@djangoproject.com",)

    # Load all the ALWAYS_INSTALLED_APPS.
    # (This import statement is intentionally delayed until after we
    # access settings because of the USE_I18N dependency.)
    from django.db.models.loading import get_apps, load_app
    get_apps()

    # Load all the test model apps.
    test_labels_set = set([label.split('.')[0] for label in test_labels])
    test_modules = get_test_modules()

    # If GeoDjango, then we'll want to add in the test applications
    # that are a part of its test suite.
    if geodjango(settings):
        from django.contrib.gis.tests import geo_apps
        test_modules.extend(geo_apps(runtests=True))

    for module_dir, module_name in test_modules:
        module_label = '.'.join([module_dir, module_name])
        # if the module was named on the command line, or
        # no modules were named (i.e., run all), import
        # this module and add it to the list to test.
        if not test_labels or module_name in test_labels_set:
            if verbosity >= 2:
                print "Importing application %s" % module_name
            mod = load_app(module_label)
            if mod:
                if module_label not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(module_label)

    return state

def run_djangotest_benchmark(trials=None, handle_argv=True, meta={}):
    if handle_argv:
        args = benchmark_parser.parse_args()
        trials = trials or args.trials
        test_label = args.param
    if 'title' not in meta:
        meta['title'] = test_label
    print_benchmark_header(test_label, meta)

    #Prepare test suite
    test_labels = [test_label]
    verbosity = 0
    state = runtests_setup(verbosity, test_labels)
    test_suite = BenchmarkTestSuiteRunner(verbosity, interactive=False,
        failfast=False)
    suite = test_suite.setup_for_benchmark(test_labels)
    for x in xrange(trials):
        start = time_f()
        benchmark_result = test_suite.run_suite(suite)
        print time_f() - start
    test_suite.teardown_for_benchmark()

def print_benchmark_header(benchmark, meta):
    if 'title' not in map(str.lower, meta.keys()):
        meta['title'] = inspect.getmodule(benchmark).__name__
    for key, value in meta.items():
        print '%s: %s' % (key.lower(), value)
    print
