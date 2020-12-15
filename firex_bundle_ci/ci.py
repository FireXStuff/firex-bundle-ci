from firexapp.engine.celery import app
from firexapp.testing.config_base import discover_tests
from celery.utils.log import get_task_logger
import datetime
import os
import subprocess
from firexapp.common import silent_mkdir
import lxml.etree as et
from xunitmerge import merge_trees


logger = get_task_logger(__name__)


@app.task(returns='flow_test_run_time')
#@flame("flow_tests_configs")
#@flame("flow_tests_file", os.path.basename)
def RunIntegrationTests(test_output_dir=None, flow_tests_configs=None, flow_tests_file=None, xunit_file_name=None,
                        uid=None, coverage=True):
    assert flow_tests_configs or flow_tests_file, 'Must provide at least flow_tests_configs or flow_tests_file'
    if not test_output_dir and uid:
        test_output_dir = os.path.join(uid.logs_dir, 'flow_test_logs')

    #if test_output_dir:
    #    self.send_flame_html(test_logs=get_link(get_firex_viewer_url(test_output_dir), 'Test Logs'))

    cmd = ['flow_tests']
    if test_output_dir:
        silent_mkdir(test_output_dir)
        cmd += ['--logs', test_output_dir]
    if flow_tests_configs:
        cmd += ['--config', flow_tests_configs]
    if flow_tests_file:
        cmd += ['--tests', flow_tests_file]
    if xunit_file_name:
        cmd += ['--xunit_file_name',  xunit_file_name]
    if coverage:
        cmd += ['--coverage']
    start = datetime.datetime.now()
    try:
        completed = subprocess.run(cmd, capture_output=True, timeout=6*60, check=True, text=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # TimeoutExpired doesn't respect text=True, so we need to decode the output
        stdout = e.stdout
        stderr = e.stderr
        if stdout:
            if not isinstance(stdout, str):
                stdout = stdout.decode()
            logger.error('Stdout:\n' + stdout)
        if stderr:
            if not isinstance(stderr, str):
                stderr = stderr.decode()
            logger.error('Stderr:\n' + stderr)
        raise
    else:
        done = datetime.datetime.now()
        if completed.stdout:
            logger.info('Stdout:\n' + completed.stdout)
        if completed.stderr:
            logger.info('Stderr:\n' + completed.stderr)

    return (done - start).total_seconds()


@app.task(bind=True)
def RunAllIntegrationTests(self, uid,
                           integration_tests_dir='tests/integration_tests/',
                           integration_tests_logs=None, coverage=True):
    if not integration_tests_logs and uid:
        test_output_dir = os.path.join(uid.logs_dir, 'integration_tests_logs')

    parallel_tasks = []

    for config in discover_tests(integration_tests_dir):
        test_config_name = config.name
        test_config_filepath = config.filepath
        test_config_output_dir = os.path.join(test_output_dir, test_config_name)
        xunit_file_name = os.path.join(test_config_output_dir, 'xunit_results.xml')
        parallel_tasks.append(RunIntegrationTests.s(uid=uid,
                                                    flow_tests_configs=test_config_name,
                                                    flow_tests_file=test_config_filepath,
                                                    test_output_dir=test_config_output_dir,
                                                    xunit_file_name=xunit_file_name,
                                                    coverage=coverage))
    if parallel_tasks:
        self.enqueue_in_parallel(parallel_tasks)
    else:
        raise AssertionError('No Integrations tests to run')

# noinspection PyPep8Naming
@app.task(returns='xunit_results')
#@flame('xunit_results', lambda location: get_link(get_firex_viewer_url(location), "xunit report"))
def AggregateXunitReports(xunit_result_files, uid, aggregated_results_file=None, known_breakages=None):
    if not len(xunit_result_files):
        raise Exception("No xml results files provided")

    xml_trees = []
    for xunit_file in xunit_result_files:
        # load xml file
        if not os.path.isfile(xunit_file):
            raise FileNotFoundError(xunit_file)
        xml_tree = et.parse(xunit_file)

        # handle cases where the root is testsuite not testsuites
        if xml_tree.getroot().tag == "testsuite":
            new_root = et.Element("testsuites")
            new_root.insert(0, xml_tree.getroot())
            # noinspection PyProtectedMember
            xml_tree._setroot(new_root)

        #strip_system_out(xml_tree)
        xml_tree.getroot().attrib.clear()  # merge_trees can barf of float point 'time'
        xml_trees.append(xml_tree)

    merged = merge_trees(*xml_trees)

    # re-compute tests, failures, errors, and time attributes
    tests = int(merged.getroot().xpath("count(testsuite/testcase)"))
    failures = int(merged.getroot().xpath("count(testsuite/testcase/failure)"))
    errors = int(merged.getroot().xpath("count(testsuite/testcase/error)"))
    merged.getroot().attrib.clear()

    merged.getroot().attrib["tests"] = str(tests)
    merged.getroot().attrib["failures"] = str(failures)
    merged.getroot().attrib["errors"] = str(errors)

    if aggregated_results_file:
        xunit_results = aggregated_results_file
    else:
        xunit_results = os.path.join(uid.logs_dir, 'xunit_results.xml')
    merged.write(xunit_results, encoding='utf-8', xml_declaration=True)

    return xunit_results