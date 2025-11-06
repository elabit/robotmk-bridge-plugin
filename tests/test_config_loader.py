import importlib.util
import json
import os
import tempfile


def _load_plugin_module():
    """Dynamically import agents_plugins/robotmk-bridge-plugin.py as a module.

    The filename contains a hyphen so we import by spec from file.
    """
    path = os.path.join(os.path.dirname(__file__), "..", "agents_plugins", "robotmk_bridge_plugin.py")
    path = os.path.normpath(path)
    spec = importlib.util.spec_from_file_location("robotmk_bridge_plugin", path)
    module = importlib.util.module_from_spec(spec)
    # Ensure the module is available in sys.modules during execution so
    # decorators like @dataclass can resolve the module namespace.
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_config_happy_path():
    module = _load_plugin_module()
    cfg_path = os.path.join(os.path.dirname(__file__), "resources", "cfg", "robotmk-bridge-plugin.json")
    configs = module.load_config(cfg_path)
    assert isinstance(configs, list)
    assert len(configs) == 2
    first = configs[0]
    assert first.path.endswith("junit-single-testsuite.xml")
    assert first.handler == "junit"
    assert first.plan == "JunitSingle"
    assert first.max_age == 3600


def test_load_config_missing_file_raises():
    module = _load_plugin_module()
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


def test_load_config_invalid_json_raises(tmp_path):
    module = _load_plugin_module()
    bad = tmp_path / "bad.json"
    bad.write_text("not a json")
    try:
        module.load_config(str(bad))
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_load_config_invalid_max_age_raises(tmp_path):
    module = _load_plugin_module()
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
