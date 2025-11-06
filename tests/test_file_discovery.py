import importlib.util
import os
import stat
import tempfile
import time


def _load_plugin_module():
    path = os.path.join(os.path.dirname(__file__), "..", "agents_plugins", "robotmk_bridge_plugin.py")
    path = os.path.normpath(path)
    spec = importlib.util.spec_from_file_location("robotmk_bridge_plugin", path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

plugin = _load_plugin_module()


def test_discover_files_concrete(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello")
    found = plugin.discover_files(str(p))
    assert found == [str(p)]


def test_discover_files_missing(tmp_path):
    p = tmp_path / "nope.txt"
    found = plugin.discover_files(str(p))
    assert found == []


def test_discover_files_glob(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    found = plugin.discover_files(str(tmp_path / "*.txt"))
    assert len(found) == 2


def test_discover_files_respects_max_age(tmp_path):
    recent = tmp_path / "recent.txt"
    stale = tmp_path / "stale.txt"
    recent.write_text("new")
    stale.write_text("old")

    cutoff = time.time() - 7200
    os.utime(stale, (cutoff, cutoff))

    found = plugin.discover_files(str(tmp_path / "*.txt"), max_age=3600)
    assert str(recent) in found
    assert str(stale) not in found


def test_stat_file_exists(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("data")
    info = plugin.stat_file(str(p))
    assert info["exists"] is True
    assert info["readable"] is True
    assert info["size"] == 4


def test_stat_file_missing(tmp_path):
    p = tmp_path / "missing.txt"
    info = plugin.stat_file(str(p))
    assert info["exists"] is False
    assert info["error"] == "not found"


def test_stat_file_unreadable(tmp_path):
    p = tmp_path / "secret.txt"
    p.write_text("secret")
    # remove read perms
    p.chmod(0)
    info = plugin.stat_file(str(p))
    # on some platforms opening may still work depending on umask; be permissive
    assert info["exists"] is True
    assert info["size"] == 6
    assert info["readable"] is False or info["error"] is not None
