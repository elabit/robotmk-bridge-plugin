from .util import module
import os
import stat
import tempfile
import time



def test_discover_files_concrete(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello")
    found = module.discover_files(str(p))
    assert found == [str(p)]


def test_discover_files_missing(tmp_path):
    p = tmp_path / "nope.txt"
    found = module.discover_files(str(p))
    assert found == []


def test_discover_files_glob(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    found = module.discover_files(str(tmp_path / "*.txt"))
    assert len(found) == 2


def test_discover_files_respects_max_age(tmp_path):
    recent = tmp_path / "recent.txt"
    stale = tmp_path / "stale.txt"
    recent.write_text("new")
    stale.write_text("old")

    cutoff = time.time() - 7200
    os.utime(stale, (cutoff, cutoff))

    found = module.discover_files(str(tmp_path / "*.txt"), max_age=3600)
    assert str(recent) in found
    assert str(stale) not in found


def test_stat_file_exists(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("data")
    info = module.stat_file(str(p))
    assert info["exists"] is True
    assert info["readable"] is True
    assert info["size"] == 4


def test_stat_file_missing(tmp_path):
    p = tmp_path / "missing.txt"
    info = module.stat_file(str(p))
    assert info["exists"] is False
    assert info["error"] == "not found"


def test_stat_file_unreadable(tmp_path):
    p = tmp_path / "secret.txt"
    p.write_text("secret")
    # remove read perms
    p.chmod(0)
    info = module.stat_file(str(p))
    # on some platforms opening may still work depending on umask; be permissive
    assert info["exists"] is True
    assert info["size"] == 6
    assert info["readable"] is False or info["error"] is not None
