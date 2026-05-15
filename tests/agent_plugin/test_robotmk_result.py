from .util import module, BASE_DIR, JUNIT_FILE, junit_config, conversion_result, conversion_result_piggyback
import base64
import json
import jsonschema
from pathlib import Path
import pytest


# Load the JSON Schema once at module level
SCHEMA_PATH = Path(__file__).parent.parent.parent / "docs" / "robotmk-json-schema.json"
with open(SCHEMA_PATH) as f:
    ROBOTMK_JSON_SCHEMA = json.load(f)


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


def test_build_robotmk_result_conforms_to_schema(conversion_result):
    """Verify that the build_robotmk_result output conforms to the JSON Schema."""
    payload = module.build_robotmk_result(conversion_result, timestamp=1234567890)
    
    # The schema validates the outer structure (host, name, content)
    jsonschema.validate(instance=payload, schema=ROBOTMK_JSON_SCHEMA)
    
    # Explicitly verify all mandatory fields in content
    content = json.loads(payload["content"])
    assert "plan_id" in content
    assert "timestamp" in content
    assert "attempts" in content
    assert len(content["attempts"]) == 1
    assert "index" in content["attempts"][0]    
    assert "outcome" in content["attempts"][0]
    assert "runtime" in content["attempts"][0]
    assert "rebot" in content
    assert "Ok" in content["rebot"]
    assert "xml" in content["rebot"]["Ok"]
    assert "html_base64" in content["rebot"]["Ok"]
    assert "timestamp" in content["rebot"]["Ok"]
    assert "config" in content
    assert "interval" in content["config"]
    assert "timeout" in content["config"]
    assert "n_attempts_max" in content["config"]
    assert "metadata" in content
    assert "application" in content["metadata"]
    assert "suite_name" in content["metadata"]
    assert "variant" in content["metadata"]


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
    
