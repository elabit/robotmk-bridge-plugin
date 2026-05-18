"""Unit tests for the test data generator fixtures."""

import pytest
from pathlib import Path
from xml.etree import ElementTree as ET


def test_temp_junit_file_fixture(temp_junit_file):
    """Verify that temp_junit_file fixture creates a valid JUnit XML file."""
    assert temp_junit_file.exists()
    assert temp_junit_file.suffix == ".xml"
    
    # Parse XML to verify structure
    tree = ET.parse(temp_junit_file)
    root = tree.getroot()
    assert root.tag == "testsuite"
    assert root.get("name") == "RobotmkBridgeTests"
    
    # Should have test cases
    testcases = root.findall("testcase")
    assert len(testcases) == 5
    
    # No failures in "passed" status
    failures = root.findall(".//failure")
    errors = root.findall(".//error")
    assert len(failures) == 0
    assert len(errors) == 0


def test_temp_junit_file_failed_fixture(temp_junit_file_failed):
    """Verify that temp_junit_file_failed fixture creates a JUnit file with failures."""
    assert temp_junit_file_failed.exists()
    
    tree = ET.parse(temp_junit_file_failed)
    root = tree.getroot()
    
    # Should have failures or errors
    failures = root.findall(".//failure")
    errors = root.findall(".//error")
    assert len(failures) + len(errors) > 0


def test_temp_gatling_file_fixture(temp_gatling_file):
    """Verify that temp_gatling_file fixture creates a valid Gatling log."""
    assert temp_gatling_file.exists()
    assert temp_gatling_file.suffix == ".log"
    
    content = temp_gatling_file.read_text()
    lines = content.strip().split("\n")
    
    # Should have RUN, USER, and REQUEST records
    assert any(line.startswith("RUN\t") for line in lines)
    assert any(line.startswith("USER\t") for line in lines)
    assert any(line.startswith("REQUEST\t") for line in lines)
    
    # Check for OK status in passed tests
    request_lines = [l for l in lines if l.startswith("REQUEST\t")]
    assert any("OK" in line for line in request_lines)


def test_temp_gatling_file_failed_fixture(temp_gatling_file_failed):
    """Verify that temp_gatling_file_failed fixture creates a Gatling log with failures."""
    assert temp_gatling_file_failed.exists()
    
    content = temp_gatling_file_failed.read_text()
    lines = content.strip().split("\n")
    
    # Should have KO (failed) requests
    request_lines = [l for l in lines if l.startswith("REQUEST\t")]
    assert any("KO" in line for line in request_lines)


def test_temp_zaproxy_file_fixture(temp_zaproxy_file):
    """Verify that temp_zaproxy_file fixture creates a valid ZAP XML report."""
    assert temp_zaproxy_file.exists()
    assert temp_zaproxy_file.suffix == ".xml"
    
    tree = ET.parse(temp_zaproxy_file)
    root = tree.getroot()
    assert root.tag == "OWASPZAPReport"
    
    # Should have alerts
    alerts = root.findall(".//alertitem")
    assert len(alerts) > 0
    
    # Check for low risk (passed status generates low-risk alerts)
    risk_codes = [alert.find("riskcode").text for alert in alerts]
    # All should be 0 (Info) or 1 (Low) for "passed" status
    assert all(int(code) <= 1 for code in risk_codes)


def test_temp_zaproxy_file_failed_fixture(temp_zaproxy_file_failed):
    """Verify that temp_zaproxy_file_failed fixture creates a ZAP report with high-risk alerts."""
    assert temp_zaproxy_file_failed.exists()
    
    tree = ET.parse(temp_zaproxy_file_failed)
    root = tree.getroot()
    
    # Should have high-risk alerts
    alerts = root.findall(".//alertitem")
    risk_codes = [int(alert.find("riskcode").text) for alert in alerts]
    # Should have at least one Medium (2) or High (3) risk
    assert any(code >= 2 for code in risk_codes)


def test_temp_test_data_dir_fixture(temp_test_data_dir):
    """Verify that temp_test_data_dir fixture provides a writable directory."""
    assert temp_test_data_dir.exists()
    assert temp_test_data_dir.is_dir()
    
    # Create a test file in the directory
    test_file = temp_test_data_dir / "test.txt"
    test_file.write_text("test content")
    
    assert test_file.exists()
    assert test_file.read_text() == "test content"
