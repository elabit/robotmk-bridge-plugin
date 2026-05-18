"""E2E tests for the test data generator fixtures."""

import pytest
from pathlib import Path


def test_e2e_test_data_fixture_creates_files(e2e_data_dir):
    """Verify that the e2e_test_data fixture generates all handler files."""
    assert e2e_data_dir.exists()
    assert e2e_data_dir.is_dir()
    
    # Check that all expected files exist
    expected_files = ["junit.xml", "gatling.log", "zaproxy.xml"]
    for filename in expected_files:
        file_path = e2e_data_dir / filename
        assert file_path.exists(), f"Missing generated file: {filename}"
        assert file_path.stat().st_size > 0, f"Generated file is empty: {filename}"


def test_e2e_junit_file_fixture(e2e_junit_file):
    """Verify that the e2e_junit_file fixture provides correct path."""
    assert e2e_junit_file.exists()
    assert e2e_junit_file.name == "junit.xml"
    content = e2e_junit_file.read_text()
    assert "<?xml" in content
    assert "<testsuite" in content


def test_e2e_gatling_file_fixture(e2e_gatling_file):
    """Verify that the e2e_gatling_file fixture provides correct path."""
    assert e2e_gatling_file.exists()
    assert e2e_gatling_file.name == "gatling.log"
    content = e2e_gatling_file.read_text()
    assert "RUN\t" in content or "REQUEST\t" in content


def test_e2e_zaproxy_file_fixture(e2e_zaproxy_file):
    """Verify that the e2e_zaproxy_file fixture provides correct path."""
    assert e2e_zaproxy_file.exists()
    assert e2e_zaproxy_file.name == "zaproxy.xml"
    content = e2e_zaproxy_file.read_text()
    assert "<?xml" in content
    assert "OWASPZAPReport" in content
