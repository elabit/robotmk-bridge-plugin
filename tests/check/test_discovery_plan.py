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
# Per-plan services
# ----------------------------------------------------------------------

def test_discover_robotmk_bridge_plan(section_payload_parsed):
    # (we get back a generator)
    results = list(module.discover_robotmk_bridge_plan(section_payload_parsed))
    assert isinstance(results[0], Service)
    assert results[0].item == "JunitSingleTest"
    assert isinstance(results[1], Service)
    assert results[1].item == "GatlingTest"

