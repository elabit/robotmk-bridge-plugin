import base64
import importlib.util
import json
import os
from pathlib import Path
import time

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
        plan_name="JunitSingleTest",
        path=JUNIT_FILE,
        handler="junit",
        max_age=3600000,
        metadata={},
    )


@pytest.fixture
def conversion_result(junit_config):
    return plugin.convert_with_handler(junit_config, JUNIT_FILE)


@pytest.fixture
def conversion_result_piggyback(junit_config):
    piggyback_cfg = plugin.Config(
        path=junit_config.path,
        handler=junit_config.handler,
        piggyback_host="ci-backend",
        max_age=junit_config.max_age,
        metadata=dict(junit_config.metadata),
    )
    return plugin.convert_with_handler(piggyback_cfg, JUNIT_FILE)


def test_resolve_handler_accepts_prefixless_name():
    """Verify that resolve_handler accepts names without an explicit namespace prefix.
    Calling plugin.resolve_handler with a bare handler name (e.g. "junit") should
    apply the default namespace and return a resolved handler object whose
    handler_key is the fully-qualified name ("rmkbridge.junit") and whose handler
    contains the expected invocation keyword ("run_junit"). This confirms the
    resolution logic correctly normalizes prefixless handler names.
    """
    resolved = plugin.resolve_handler("junit")
    assert resolved.handler_key == "rmkbridge.junit"
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
    - The handler identifies itself as the JUnit handler ("rmkbridge.junit") and exposes the expected keyword ("run_junit").
    - The produced Robot output XML contains the "JUnit Execution" marker.
    - A non-empty HTML log is produced and contains an HTML root element.

    This ensures the conversion pipeline recognizes JUnit inputs and emits Robot-compatible outputs (robot_output_xml and log_html).
    """
    result = plugin.convert_with_handler(junit_config, JUNIT_FILE)
    assert result.handler_key == "rmkbridge.junit"
    assert result.handler_keyword == "run_junit"
    assert "JUnit Execution" in result.robot_output_xml
    assert result.log_html is not None
    assert "<html" in result.log_html.lower()


def test_convert_with_handler_unknown_handler_raises():
    cfg = plugin.Config(path="/tmp/does-not-matter", handler="nope", max_age=1, metadata={})
    with pytest.raises(plugin.HandlerResolutionError):
        plugin.convert_with_handler(cfg, cfg.path)


def test_build_robotmk_result_structure(conversion_result):
    payload = plugin.build_robotmk_result(conversion_result, timestamp=1234567890)

    assert payload["host"] == "Source"
    assert payload["name"]

    content = json.loads(payload["content"])    
    assert content["timestamp"] == 1234567890
    # TODO
    assert content["attempts"][0]["outcome"] == "AllTestsPassed"
    assert content["rebot"]["Ok"]["xml"].startswith("<?xml")

    html_base64 = content["rebot"]["Ok"]["html_base64"]
    decoded_html = base64.b64decode(html_base64.encode("ascii")) if html_base64 else b""
    assert b"<html" in decoded_html.lower()


def test_build_robotmk_result_uses_piggyback_host(conversion_result_piggyback):
    payload = plugin.build_robotmk_result(conversion_result_piggyback)

    assert payload["host"] == "ci-backend"


def test_resolve_results_directory_reads_robotmk_config(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    config_path = tmp_path / "robotmk.json"
    config_path.write_text(json.dumps({"runtime_directory": str(runtime_dir)}))

    resolved = plugin.resolve_results_directory(robotmk_config_path=str(config_path))
    assert resolved == runtime_dir / "results" / "plans"


def test_write_robotmk_result_creates_plan_file(conversion_result, tmp_path):
    payload = plugin.build_robotmk_result(conversion_result, timestamp=123)

    target = plugin.write_robotmk_result(conversion_result.config.plan_name, payload, results_dir=str(tmp_path))

    expected = Path(tmp_path) / f"{conversion_result.config.plan_name}.json"
    assert target == expected
    stored = json.loads(expected.read_text(encoding="utf-8"))
    assert stored["host"] == payload["host"]
    assert json.loads(stored["content"])["timestamp"] == 123


def test_process_config_entry_creates_result_file(tmp_path, junit_config):
    records = plugin.process_config_entry(
        junit_config,
        reference_time=123456,
        results_dir=str(tmp_path),
    )

    assert len(records) == 1
    record = records[0]
    assert record.status == "success"
    assert record.timestamp == 123456
    assert record.result_path is not None
    stored_path = Path(record.result_path)
    assert stored_path.exists()
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert json.loads(stored["content"])["timestamp"] == 123456


def test_run_bridge_processes_config_and_writes_results(tmp_path, junit_config):
    config_file = tmp_path / "robotmk-bridge-plugin.json"
    config_payload = {
        "paths": [
            {
                "path": junit_config.path,
                "handler": junit_config.handler,
                "plan_name": junit_config.plan_name,
                "max_age": junit_config.max_age
            }
        ]
    }
    config_file.write_text(json.dumps(config_payload))

    results_dir = tmp_path / "results"
    report = plugin.run_bridge(
        config_path=str(config_file),
        results_dir=str(results_dir),
        reference_time=987654321,
    )

    assert len(report.records) == 1
    record = report.records[0]
    assert record.status == "success"
    assert record.result_path is not None
    stored = json.loads(Path(record.result_path).read_text(encoding="utf-8"))
    assert json.loads(stored["content"])["timestamp"] == 987654321


def test_build_agent_payload_contains_summary(tmp_path, junit_config):
    reference_time = os.path.getmtime(JUNIT_FILE) + 10
    records = plugin.process_config_entry(
        junit_config,
        results_dir=str(tmp_path),
        reference_time=reference_time,
    )
    report = plugin.BridgeRunReport(
        started_at=time.time() - 1,
        finished_at=time.time(),
        records=records,
        config_count=1,
        messages=["test message"],
    )

    payload = plugin.build_agent_payload(report)
    assert payload["summary"]["files_success"] == 1
    assert "plans" in payload
    assert payload["messages"] == ["test message"]