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
    "summary,state_expected",
    [
        ({"configs": 1, "files_total": 2, "files_success": 2, "files_missing": 0, "files_error": 0}, State.OK),
        ({"configs": 1, "files_total": 2, "files_success": 1, "files_missing": 1, "files_error": 0}, State.WARN),
        ({"configs": 1, "files_total": 2, "files_success": 1, "files_missing": 0, "files_error": 1}, State.CRIT),
    ],
)
def test_check_robotmk_bridge_state_from_summary(summary, state_expected):
    section = {
        "summary": summary,
        "runtime_s": 0.234,
    }

    results = list(module.check_robotmk_bridge(section))

    # first yield is Result, then metrics
    assert isinstance(results[0], Result)
    assert results[0].state == state_expected


def test_check_robotmk_bridge_summary_message_content():
    section = {
        "summary": {
            "configs": 2,
            "files_total": 5,
            "files_success": 3,
            "files_missing": 1,
            "files_error": 1,
        },
        "runtime_s": 1.2345,
    }

    results = list(module.check_robotmk_bridge(section))
    result = results[0]

    assert isinstance(result, Result)
    # basic content checks
    msg = result.summary
    assert "2 configs" in msg
    assert "5 files" in msg
    assert "success: 3" in msg
    assert "missing: 1" in msg
    assert "error: 1" in msg
    # runtime formatted to 3 decimals
    assert "runtime: 1.234s" in msg


def test_check_robotmk_bridge_yields_expected_metrics():
    section = {
        "summary": {
            "configs": 1,
            "files_total": 4,
            "files_success": 4,
            "files_missing": 0,
            "files_error": 0,
        },
        "runtime_s": 0.5,
    }

    results = list(module.check_robotmk_bridge(section))

    # first is Result, rest are Metric objects
    result_obj = results[0]
    metric_objs = results[1:]

    assert isinstance(result_obj, Result)
    assert all(isinstance(m, Metric) for m in metric_objs)

    metrics_by_name = {m.name: m.value for m in metric_objs}

    assert metrics_by_name["runtime"] == pytest.approx(0.5)
    assert metrics_by_name["files_total"] == 4
    assert metrics_by_name["files_success"] == 4
    assert metrics_by_name["files_missing"] == 0
    assert metrics_by_name["files_error"] == 0