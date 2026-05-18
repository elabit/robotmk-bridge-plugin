"""E2E test configuration and fixtures.

This conftest.py sets up the e2e test environment by generating
test data files using the shared data generator.
"""

import os
from pathlib import Path
import pytest

from tests.data_generator import generate_all_handler_files


# Default e2e data directory
DEFAULT_E2E_DATA_DIR = Path(__file__).parent / "data"
E2E_DATA_DIR = Path(os.getenv("BRIDGE_E2E_DATA_DIR", str(DEFAULT_E2E_DATA_DIR)))


@pytest.fixture(scope="session", autouse=True)
def e2e_test_data():
    """Generate test data files for all handlers before running e2e tests.
    
    This fixture runs once per test session and creates test result files
    in the E2E_DATA_DIR for each supported handler (JUnit, Gatling, ZAP).
    
    The directory is configurable via BRIDGE_E2E_DATA_DIR environment variable.
    """
    # Ensure data directory exists
    E2E_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate test files for all handlers
    files = generate_all_handler_files(
        output_dir=E2E_DATA_DIR,
        test_status="passed",  # Default to passing tests
        filename_pattern="{handler}.{ext}"
    )
    
    print(f"\n[E2E] Generated test data in {E2E_DATA_DIR}:")
    for handler, path in files.items():
        print(f"  - {handler}: {path.name}")
    
    return files


@pytest.fixture
def e2e_data_dir() -> Path:
    """Provide the path to the e2e data directory.
    
    Returns:
        Path to the directory containing generated test data files.
        
    Example:
        def test_agent_plugin_reads_junit_file(e2e_data_dir):
            junit_file = e2e_data_dir / "junit.xml"
            assert junit_file.exists()
    """
    return E2E_DATA_DIR


@pytest.fixture
def e2e_junit_file(e2e_data_dir) -> Path:
    """Provide path to the generated JUnit test file."""
    return e2e_data_dir / "junit.xml"


@pytest.fixture
def e2e_gatling_file(e2e_data_dir) -> Path:
    """Provide path to the generated Gatling test file."""
    return e2e_data_dir / "gatling.log"


@pytest.fixture
def e2e_zaproxy_file(e2e_data_dir) -> Path:
    """Provide path to the generated ZAP test file."""
    return e2e_data_dir / "zaproxy.xml"
