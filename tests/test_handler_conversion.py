import importlib.util
import os

import pytest


def _load_plugin_module():
    path = os.path.join(os.path.dirname(__file__), "..", "agents_plugins", "robotmk_bridge_plugin.py")
    path = os.path.normpath(path)
    spec = importlib.util.spec_from_file_location("robotmk_bridge_plugin", path)
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


plugin = _load_plugin_module()
BASE_DIR = os.path.join(os.path.dirname(__file__), "resources", "test_output")
JUNIT_FILE = os.path.join(BASE_DIR, "junit", "junit-single-testsuite.xml")


class DummyHandler:
    def __init__(self):
        self.keyword = "dummy_keyword"

    def parse_results(self, result_file, threshold, optional=None):
        return {"name": result_file, "metadata": {"threshold": threshold, "optional": optional}}


@pytest.fixture(scope="module")
def junit_config():
    return plugin.Config(
        path=JUNIT_FILE,
        handler="junit",
        max_age=3600,
        metadata={},
    )


def test_resolve_handler_accepts_prefixless_name():
    """Verify that resolve_handler accepts names without an explicit namespace prefix.
    Calling plugin.resolve_handler with a bare handler name (e.g. "junit") should
    apply the default namespace and return a resolved handler object whose
    handler_key is the fully-qualified name ("oxygen.junit") and whose handler
    contains the expected invocation keyword ("run_junit"). This confirms the
    resolution logic correctly normalizes prefixless handler names.
    """
    resolved = plugin.resolve_handler("junit")
    assert resolved.handler_key == "oxygen.junit"
    assert resolved.handler.keyword == "run_junit"


def test_prepare_handler_call_requires_metadata():
    """
    Verify that plugin._prepare_handler_call enforces required metadata and
    correctly constructs call arguments.
    This test checks two behaviors:
    1. If required metadata is missing (empty metadata dict), a
        plugin.HandlerConfigurationError is raised.
    2. If required and optional metadata are provided, the function returns
        the expected positional and keyword arguments:
        - The returned args list contains the provided filepath ("result.xml").
        - The returned kwargs include the required "threshold" and the
          optional "optional" entries with their supplied values.
    Ensures metadata validation and correct splitting of positional vs.
    keyword parameters for handler invocation.
    """

    handler = DummyHandler()
    with pytest.raises(plugin.HandlerConfigurationError):
        plugin._prepare_handler_call(handler, "result.xml", {})

    args, kwargs = plugin._prepare_handler_call(handler, "result.xml", {"threshold": 5, "optional": 1})
    assert args == ["result.xml"]
    assert kwargs["threshold"] == 5
    assert kwargs["optional"] == 1


def test_convert_with_handler_returns_robot_artifacts(junit_config):
    """
    Verify that convert_with_handler produces the expected Robot artifacts for a JUnit input.

    The test calls plugin.convert_with_handler with a junit_config fixture and a JUnit file path and asserts:
    - The handler identifies itself as the JUnit handler ("oxygen.junit") and exposes the expected keyword ("run_junit").
    - The produced Robot output XML contains the "JUnit Execution" marker.
    - A non-empty HTML log is produced and contains an HTML root element.

    This ensures the conversion pipeline recognizes JUnit inputs and emits Robot-compatible outputs (robot_output_xml and log_html).
    """
    result = plugin.convert_with_handler(junit_config, JUNIT_FILE)
    assert result.handler_key == "oxygen.junit"
    assert result.handler_keyword == "run_junit"
    assert "JUnit Execution" in result.robot_output_xml
    assert result.log_html is not None
    assert "<html" in result.log_html.lower()


def test_convert_with_handler_unknown_handler_raises():
    cfg = plugin.Config(path="/tmp/does-not-matter", handler="nope", max_age=1, metadata={})
    with pytest.raises(plugin.HandlerResolutionError):
        plugin.convert_with_handler(cfg, cfg.path)