from .util import module, section_payload_string, section_payload_parsed
import base64
import os
from pathlib import Path
import time
from .util import module
from cmk.ccc.exceptions import MKGeneralException
from cmk.agent_based.v2 import AgentSection, CheckPlugin, Service, Result, State, Metric, IgnoreResultsError
import pytest


@pytest.mark.parametrize(
    "item, status, state",
    [
        ("JunitSingleTest", "success", State.OK),
        ("GatlingTest", "error", State.CRIT),
        ("GatlingTest", "missing", State.WARN)
    ]
)
def test_check_robotmk_bridge_plan(item, status, state, section_payload_parsed):
    section_payload_parsed['plans'][item]['files'][0]['status'] = status
    # Pass empty params dict (uses defaults)
    params = {}
    # (we get back a generator)
    results = list(module.check_robotmk_bridge_plan(item, params, section_payload_parsed))

    # --- Assertions ---
    # 1. First element must be a Result
    result = results[0]
    assert isinstance(result, Result)

    # 2. State must be OK for this test data
    assert result.state == state

    # 3. Summary contains correct information
    assert item in result.summary
    assert "success" in result.summary

    # 4. Remaining items must be Metric objects
    metrics = results[1:]
    assert all(isinstance(m, Metric) for m in metrics)

    # 5. Convert metrics to a usable dict
    metric_values = {m.name: m.value for m in metrics}

    assert metric_values["plan_files_total"] == 1
    assert metric_values["plan_files_success"] == int(status == "success")
    assert metric_values["plan_files_error"] == int(status == "error")
    assert metric_values["plan_files_missing"] == int(status == "missing")