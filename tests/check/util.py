import importlib.util
import os
import pytest
import time
import copy 
import json


def _load_plugin_module():
    """Dynamically import agent_plugins/robotmk-bridge-plugin.py as a module.

    The filename contains a hyphen so we import by spec from file.
    """
    path = os.path.join(os.path.dirname(__file__), "../..", "checks", "robotmk_bridge_plugin.py")
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

ROBOTMK_BRIDGE_BASE_DATA = {
    "timestamp": 1763113239,
    "runtime_s": 0.23404693603515625,
    "summary": {
        "configs": 2,
        "files_total": 2,
        "files_success": 2,
        "files_missing": 0,
        "files_error": 0,
    },
    "plans": {
        "JunitSingleTest": {
            "handler": "junit",
            "host": "Source",
            "files": [
                {
                    "plan": "JunitSingleTest",
                    "handler": "junit",
                    "source_path": "/workspaces/robotmk-bridge-plugin/tests/resources/test_output/junit/junit-single-testsuite.xml",
                    "status": "success",
                    "runtime_s": 0.06521021100343205,
                    "result_path": "/var/lib/check_mk_agent/robotmk/scheduler/results/plans/JunitSingleTest.json",
                    "host": "Source",
                    "message": None,
                    "timestamp": 1763113239,
                }
            ],
        },
        "GatlingTest": {
            "handler": "gatling",
            "host": "Source",
            "files": [
                {
                    "plan": "GatlingTest",
                    "handler": "gatling",
                    "source_path": "/workspaces/robotmk-bridge-plugin/tests/resources/test_output/gatling/gatling-example-simulation.log",
                    "status": "success",
                    "runtime_s": 0.14350915301474743,
                    "result_path": "/var/lib/check_mk_agent/robotmk/scheduler/results/plans/GatlingTest.json",
                    "host": "Source",
                    "message": None,
                    "timestamp": 1763113239,
                }
            ],
        },
    },
    "messages": [],
}


@pytest.fixture
def section_payload_parsed():
    """Parsed data structure as used by the check functions."""
    return copy.deepcopy(ROBOTMK_BRIDGE_BASE_DATA)


@pytest.fixture
def section_payload_string():
    """Agent-style string_table (as Checkmk passes it to the parser)."""
    string_payload = json.dumps(ROBOTMK_BRIDGE_BASE_DATA, separators=(",", ":"))
    # We emulate the agent section: list of rows, each row = list of columns (string)
    return [[string_payload]]

@pytest.fixture
def item(section_payload_parsed):
    """Returns the first key of the dict"""
    return next(iter(section_payload_parsed['plans']))