"""Root conftest.py for unit tests.

Provides fixtures for generating test data files in temporary locations
for unit testing purposes.
"""

import tempfile
from pathlib import Path
import pytest

from tests.data_generator import generate_handler_file


@pytest.fixture
def temp_junit_file():
    """Generate a temporary JUnit XML file for testing.
    
    Yields:
        Path to a temporary JUnit XML file with passing tests.
        
    The file is automatically cleaned up after the test.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        generate_handler_file(
            handler_name="junit",
            output_path=tmp_path,
            test_status="passed",
            num_tests=5
        )
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def temp_junit_file_failed():
    """Generate a temporary JUnit XML file with failing tests.
    
    Yields:
        Path to a temporary JUnit XML file with failed tests.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        generate_handler_file(
            handler_name="junit",
            output_path=tmp_path,
            test_status="failed",
            num_tests=5
        )
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def temp_gatling_file():
    """Generate a temporary Gatling log file for testing.
    
    Yields:
        Path to a temporary Gatling simulation.log file with passing requests.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        generate_handler_file(
            handler_name="gatling",
            output_path=tmp_path,
            test_status="passed",
            num_requests=10
        )
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def temp_gatling_file_failed():
    """Generate a temporary Gatling log file with failing requests.
    
    Yields:
        Path to a temporary Gatling simulation.log file with failed requests.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        generate_handler_file(
            handler_name="gatling",
            output_path=tmp_path,
            test_status="failed",
            num_requests=10
        )
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def temp_zaproxy_file():
    """Generate a temporary ZAP XML file for testing.
    
    Yields:
        Path to a temporary OWASP ZAP report file with low-risk alerts.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        generate_handler_file(
            handler_name="zaproxy",
            output_path=tmp_path,
            test_status="passed",
            num_alerts=5
        )
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def temp_zaproxy_file_failed():
    """Generate a temporary ZAP XML file with high-risk alerts.
    
    Yields:
        Path to a temporary OWASP ZAP report file with high-risk security issues.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        generate_handler_file(
            handler_name="zaproxy",
            output_path=tmp_path,
            test_status="failed",
            num_alerts=5
        )
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def temp_test_data_dir():
    """Create a temporary directory for test data.
    
    Yields:
        Path to a temporary directory that is cleaned up after the test.
        
    Example:
        def test_something(temp_test_data_dir):
            test_file = temp_test_data_dir / "data.txt"
            test_file.write_text("test")
            assert test_file.exists()
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
