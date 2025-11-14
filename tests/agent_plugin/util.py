import importlib.util
import os
import pytest
import time



BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "test_output")
JUNIT_FILE = os.path.join(BASE_DIR, "junit", "junit-single-testsuite.xml")

def _load_plugin_module():
    """Dynamically import agent_plugins/robotmk-bridge-plugin.py as a module.

    The filename contains a hyphen so we import by spec from file.
    """
    path = os.path.join(os.path.dirname(__file__), "../..", "agent_plugins", "robotmk_bridge_plugin.py")
    path = os.path.normpath(path)
    spec = importlib.util.spec_from_file_location("robotmk_bridge_plugin", path)
    module = importlib.util.module_from_spec(spec)
    # Ensure the module is available in sys.modules during execution so
    # decorators like @dataclass can resolve the module namespace.
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

module = _load_plugin_module()

@pytest.fixture(scope="module")
def junit_config():
    return module.Config(
        plan_name="JunitSingleTest",
        path=JUNIT_FILE,
        handler="junit",
        max_age=3600000,
        metadata={},
    )


@pytest.fixture
def conversion_result(junit_config):
    return module.convert_with_handler(junit_config, JUNIT_FILE)


@pytest.fixture
def conversion_result_piggyback(junit_config):
    piggyback_cfg = module.Config(
        path=junit_config.path,
        handler=junit_config.handler,
        piggyback_host="ci-backend",
        max_age=junit_config.max_age,
        metadata=dict(junit_config.metadata),
    )
    return module.convert_with_handler(piggyback_cfg, JUNIT_FILE)

@pytest.fixture
def file_run_record(tmp_path, junit_config):
    reference_time = os.path.getmtime(JUNIT_FILE) + 10
    records = module.process_config_entry(
        junit_config,
        results_dir=str(tmp_path),
        reference_time=reference_time,
    )  
    return records  

@pytest.fixture
def bridge_run_report(file_run_record):
    report = module.BridgeRunReport(
        started_at=time.time() - 1,
        finished_at=time.time(),
        records=file_run_record,
        config_count=1,
        messages=["test message"],
    )    
    return report