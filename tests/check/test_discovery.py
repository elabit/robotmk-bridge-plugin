from .util import module, section_payload_string, section_payload_parsed, item
import base64
import os
from pathlib import Path
import time
from .util import module
from cmk.ccc.exceptions import MKGeneralException
from cmk.agent_based.v2 import AgentSection, CheckPlugin, Service, Result, State, Metric, IgnoreResultsError
import pytest

# ----------------------------------------------------------------------
# Status service
# ----------------------------------------------------------------------


def test_parse_robotmk_bridge_returns_inner_json():
    string_table = [['{"foo": "bar", "baz": {"one": 1, "two": 2, "three": 3}}']]
    parsed_data = module.parse_robotmk_bridge(string_table)
    assert "foo" in parsed_data
    assert "baz" in parsed_data
    assert "one" in parsed_data["baz"]    
    
def test_fail_parse_robotmk_bridge_with_invalid_json():
    non_string_table = "abcd"
    with pytest.raises(MKGeneralException, match="Invalid JSON payload"):
        module.parse_robotmk_bridge(non_string_table)

def test_parse_robotmk_bridge_agent_payload(section_payload_string):
    section = module.parse_robotmk_bridge(section_payload_string)
    assert section["summary"]["files_success"] == 2

def test_discover_robotmk_bridge(section_payload_parsed):
    # (we get back a generator)
    (service,) = module.discover_robotmk_bridge(section_payload_parsed)
    assert isinstance(service, Service)

