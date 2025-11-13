from .util import module, bridge_run_report, file_run_record, junit_config
import base64
import json
import os
from pathlib import Path
import time

import pytest





def test_build_agent_payload_contains_summary(bridge_run_report):
    payload = module.build_agent_payload(bridge_run_report)
    assert "summary" in payload
    assert payload["summary"]["files_success"] == 1
    assert payload["summary"]["files_total"] == 1
    assert payload["summary"]["files_missing"] == 0
    assert payload["summary"]["files_error"] == 0

    assert "plans" in payload
    assert payload["plans"]["JunitSingleTest"]["handler"] == "junit"
    assert payload["messages"] == ["test message"]

def test_print_agent_section(capsys, bridge_run_report):
    pass
    module.print_agent_section(bridge_run_report)
    captured = capsys.readouterr()
    stdout = captured.out.strip()
    assert stdout.startswith("<<<robotmk_bridge>>>"), "Agent section missing!"

