from .util import _load_plugin_module, BASE_DIR, JUNIT_FILE, junit_config, conversion_result, conversion_result_piggyback
import base64
import json
import os
from pathlib import Path
import time
from .util import module

import pytest




class DummyHandler:
    def __init__(self):
        self.keyword = "dummy_keyword"

    def parse_results(self, result_file, threshold, optional=None):
        return {"name": result_file, "metadata": {"threshold": threshold, "optional": optional}}



def test_resolve_handler_accepts_prefixless_name():
    """Verify that resolve_handler accepts names without an explicit namespace prefix.
    Calling module.resolve_handler with a bare handler name (e.g. "junit") should
    apply the default namespace and return a resolved handler object whose
    handler_key is the fully-qualified name ("rmkbridge.junit") and whose handler
    contains the expected invocation keyword ("run_junit"). This confirms the
    resolution logic correctly normalizes prefixless handler names.
    """
    resolved = module.resolve_handler("junit")
    assert resolved.handler_key == "rmkbridge.junit"
    assert resolved.handler.keyword == "run_junit"


def test_prepare_handler_call_requires_metadata():
    """
    Verify that module._prepare_handler_call enforces required metadata and
    correctly constructs call arguments.
    This test checks two behaviors:
    1. If required metadata is missing (empty metadata dict), a
        module.HandlerConfigurationError is raised.
    2. If required and optional metadata are provided, the function returns
        the expected positional and keyword arguments:
        - The returned args list contains the provided filepath ("result.xml").
        - The returned kwargs include the required "threshold" and the
          optional "optional" entries with their supplied values.
    Ensures metadata validation and correct splitting of positional vs.
    keyword parameters for handler invocation.
    """

    handler = DummyHandler()
    with pytest.raises(module.HandlerConfigurationError):
        module._prepare_handler_call(handler, "result.xml", {})

    args, kwargs = module._prepare_handler_call(handler, "result.xml", {"threshold": 5, "optional": 1})
    assert args == ["result.xml"]
    assert kwargs["threshold"] == 5
    assert kwargs["optional"] == 1