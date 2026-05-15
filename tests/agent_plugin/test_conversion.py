from .util import module, JUNIT_FILE, junit_config, conversion_result, conversion_result_piggyback
import base64
import json
import os
from pathlib import Path
import time

import pytest




class DummyHandler:
    def __init__(self):
        self.keyword = "dummy_keyword"

    def parse_results(self, result_file, threshold, optional=None):
        return {"name": result_file, "metadata": {"threshold": threshold, "optional": optional}}



def test_convert_with_handler_returns_robot_artifacts(junit_config):
    """
    Verify that convert_with_handler produces the expected Robot artifacts for a JUnit input.

    The test calls module.convert_with_handler with a junit_config fixture and a JUnit file path and asserts:
    - The handler identifies itself as the JUnit handler ("rmkbridge.junit") and exposes the expected keyword ("run_junit").
    - The produced Robot output XML contains the "JUnit Execution" marker.
    - A non-empty HTML log is produced and contains an HTML root element.

    This ensures the conversion pipeline recognizes JUnit inputs and emits Robot-compatible outputs (robot_output_xml and log_html).
    """
    result = module.convert_with_handler(junit_config, JUNIT_FILE)
    assert result.handler_key == "rmkbridge.junit"
    assert result.handler_keyword == "run_junit"
    assert "JUnit Execution" in result.robot_output_xml
    assert result.log_html is not None
    assert "<html" in result.log_html.lower()


def test_convert_with_handler_unknown_handler_raises():
    cfg = module.Config(
        plan_name="test",
        path="/tmp/does-not-matter",
        handler="nope",
        source_mode="single_file",
        metadata={}
    )
    with pytest.raises(module.HandlerResolutionError):
        module.convert_with_handler(cfg, cfg.path)




def test_resolve_results_directory_reads_robotmk_config(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    config_path = tmp_path / "robotmk.json"
    config_path.write_text(json.dumps({"runtime_directory": str(runtime_dir)}))

    resolved = module.resolve_results_directory(robotmk_config_path=str(config_path))
    assert resolved == runtime_dir / "results" / "plans"


def test_fail_process_config_entry_without_candidates(monkeypatch: pytest.MonkeyPatch, tmp_path, junit_config):
    # Monkeypatch discover_source_files (not discover_files) to return empty list
    monkeypatch.setattr(module, "discover_source_files", lambda *args, **kwargs: [])
    records = module.process_config_entry(
        junit_config,
        reference_time=123456,
        results_dir=str(tmp_path),
    )    
    assert len(records) == 1
    assert records[0].message == "no files matched pattern"
    assert records[0].status == "missing"



def test_process_config_entry_creates_result_file(tmp_path, junit_config):
    records = module.process_config_entry(
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
    # The timestamp in content uses file mtime, not reference_time
    content = json.loads(stored["content"])
    file_mtime = os.path.getmtime(junit_config.path)
    assert content["timestamp"] == int(file_mtime)


def test_run_bridge_processes_config_and_writes_results(tmp_path, junit_config):
    config_file = tmp_path / "robotmk-bridge-module.json"
    # Use legacy paths format (still supported for backward compat)
    config_payload = {
        "paths": [
            {
                "path": junit_config.path,
                "handler": junit_config.handler,
                "plan_name": junit_config.plan_name,
            }
        ]
    }
    config_file.write_text(json.dumps(config_payload))

    results_dir = tmp_path / "results"
    report = module.run_bridge(
        config_path=str(config_file),
        results_dir=str(results_dir),
        reference_time=987654321,
    )

    assert len(report.records) == 1
    record = report.records[0]
    assert record.status == "success"
    assert record.result_path is not None
    stored = json.loads(Path(record.result_path).read_text(encoding="utf-8"))
    # The timestamp in content uses file mtime, not reference_time
    content = json.loads(stored["content"])
    file_mtime = os.path.getmtime(junit_config.path)
    assert content["timestamp"] == int(file_mtime)

