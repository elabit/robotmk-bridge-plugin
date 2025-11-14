from .util import module, BASE_DIR, JUNIT_FILE, junit_config, conversion_result, conversion_result_piggyback
import base64
import json
from pathlib import Path
import pytest


def test_build_robotmk_result_structure(conversion_result):
    payload = module.build_robotmk_result(conversion_result, timestamp=1234567890)

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
    payload = module.build_robotmk_result(conversion_result_piggyback)

    assert payload["host"] == "ci-backend"


def test_write_robotmk_result_creates_plan_file(conversion_result, tmp_path):
    payload = module.build_robotmk_result(conversion_result, timestamp=123)

    target = module.write_robotmk_result(conversion_result.config.plan_name, payload, results_dir=str(tmp_path))

    expected = Path(tmp_path) / f"{conversion_result.config.plan_name}.json"
    assert target == expected
    stored = json.loads(expected.read_text(encoding="utf-8"))
    assert stored["host"] == payload["host"]
    assert json.loads(stored["content"])["timestamp"] == 123

def test_fail_write_robotmk_result_wo_plan(conversion_result, tmp_path):
    payload = module.build_robotmk_result(conversion_result, timestamp=123)
    
    with pytest.raises(ValueError, match="Result payload missing string"):
        module.write_robotmk_result(None, payload, results_dir=str(tmp_path))
    
