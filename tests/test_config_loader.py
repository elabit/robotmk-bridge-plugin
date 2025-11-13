import json
import os
import tempfile
from .util import module
import pytest
from pathlib import Path
import re



@pytest.fixture
def robotmk_config_path(tmp_path) -> Path:
    cfg_path = tmp_path / "robotmk.json"
    payload = {
        "runtime_directory": str(tmp_path / "runtime")
    }
    with open(cfg_path, "w") as f:
        json.dump(payload, f)
    return cfg_path


def test_load_config_happy_path(tmp_path):
    cfg_path = tmp_path / "robotmk-bridge-plugin.json"
    payload = {
        "paths": [
            {
                "path": os.path.join("../", "junit-single-testsuite.xml"),
                "handler": "junit",
                "plan_name": "JunitSingleTest",
                "max_age": 36000000000000
            },
            {
                "path": os.path.join("../", "gatling-example-simulation.log"),
                "handler": "gatling",
                "plan_name": "GatlingTest",
                "max_age": 36000000000000
            },
        ]
    }
    with open(cfg_path, "w") as f:
        json.dump(payload, f)
    configs = module.load_config(cfg_path)
    assert isinstance(configs, list)
    assert len(configs) == 2
    first = configs[0]
    # TODO: enable again
    #assert first.max_age == 3600
    assert first.path.endswith("junit-single-testsuite.xml")
    assert first.handler == "junit"
    assert first.plan_name == "JunitSingleTest"
    assert first.piggyback_host is None
    assert first.max_age == 36000000000000
    
    second = configs[1]
    # TODO: enable again
    #assert second.max_age == 3600    
    assert second.path.endswith("gatling-example-simulation.log")
    assert second.handler == "gatling"
    assert second.plan_name == "GatlingTest"
    # TODO: Implement later
    #assert second.piggyback_host == "bridge-gatling-host"


def test_load_config_missing_file_raises():
    missing = os.path.join(tempfile.gettempdir(), "no-such-config-hopefully.json")
    try:
        os.remove(missing)
    except OSError:
        pass
    try:
        module.load_config(missing)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass

def test_fail_load_robotmk_scheduler_working_directory_wo_config_path():
    with pytest.raises(FileNotFoundError, match="robotmk config not found: /etc/check_mk/robotmk.json"):
        path = module.resolve_results_directory()


def test_fail_load_robotmk_scheduler_working_directory_wo_runtime_dir(tmp_path):
    bad_cfg = tmp_path / "bad.json"
    bad_cfg.write_text("{}")
    with pytest.raises(ValueError, match="robotmk config missing valid 'runtime_directory'"):
        path = module.resolve_results_directory(robotmk_config_path=bad_cfg)

def test_load_robotmk_scheduler_working_directory_w_mkconfdir_envvar(monkeypatch: pytest.MonkeyPatch):
    if os.name != "nt":
        # Linux/Mac
        path = "/etc/someotherpath/check_mk/conf"        
    else:
        # Windows
        path = "C:/someotherpath/check_mk/conf"
    os.environ["MK_CONFDIR"] = path
    rmkcfg = Path(path) / "robotmk.json"
    with pytest.raises(FileNotFoundError, match=f"robotmk config not found: {rmkcfg}"):
        path = module.resolve_results_directory()


def test_load_robotmk_scheduler_working_directory(robotmk_config_path):
    path = module.resolve_results_directory(robotmk_config_path=robotmk_config_path)
    assert re.search(r".*runtime/results/plans", str(path))



def test_load_config_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not a json")
    try:
        module.load_config(str(bad))
        assert False, "Expected ValueError"
    except ValueError:
        pass




def test_load_config_invalid_max_age_raises(tmp_path):
    cfg_file = tmp_path / "invalid_max_age.json"
    payload = {
        "paths": [
            {
                "path": "/tmp/example.xml",
                "handler": "noop",
                "max_age": -5,
            }
        ]
    }
    cfg_file.write_text(json.dumps(payload))
    try:
        module.load_config(str(cfg_file))
        assert False, "Expected ValueError for negative max_age"
    except ValueError:
        pass
