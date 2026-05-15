"""JUnit XML test data generator."""

import random
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Dict


def generate(
    output_path: Path,
    test_status: str = "passed",
    handler_def: Dict = None,
    num_tests: int = 5,
    duration_s: float = 2.5,
    **kwargs
) -> None:
    """Generate a JUnit XML result file.
    
    Args:
        output_path: Path where the XML file should be written
        test_status: 'passed', 'failed', or 'mixed'
        handler_def: Handler definition from handlers.yaml (unused here)
        num_tests: Number of test cases to generate
        duration_s: Total duration in seconds
        **kwargs: Additional parameters (ignored)
    """
    # Create root testsuite element
    testsuite = ET.Element("testsuite")
    testsuite.set("name", "RobotmkBridgeTests")
    testsuite.set("tests", str(num_tests))
    testsuite.set("time", f"{duration_s:.3f}")
    testsuite.set("timestamp", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    
    failures = 0
    errors = 0
    
    # Generate test cases based on test_status
    for i in range(num_tests):
        testcase = ET.SubElement(testsuite, "testcase")
        testcase.set("classname", f"tests.example.TestSuite{i // 3 + 1}")
        testcase.set("name", f"test_example_{i + 1}")
        # Add variance: +/- 30% of average time
        avg_time = duration_s / num_tests
        test_time = avg_time * random.uniform(0.7, 1.3)
        testcase.set("time", f"{test_time:.3f}")
        
        # Determine if this test should fail
        should_fail = False
        if test_status == "failed":
            should_fail = True
        elif test_status == "mixed" and i % 3 == 0:
            should_fail = True
        
        if should_fail:
            if i % 2 == 0:
                # Add failure
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", f"Assertion failed: Expected value was incorrect")
                failure.set("type", "AssertionError")
                failure.text = f"AssertionError: Expected 'success' but got 'failure' at line {i * 10 + 42}"
                failures += 1
            else:
                # Add error
                error = ET.SubElement(testcase, "error")
                error.set("message", f"Test runtime error")
                error.set("type", "RuntimeError")
                error.text = f"RuntimeError: Connection timeout after 30 seconds"
                errors += 1
        else:
            # Optionally add system-out for passed tests
            if i % 2 == 0:
                system_out = ET.SubElement(testcase, "system-out")
                system_out.text = f"Test {i + 1} executed successfully with no warnings"
    
    # Update testsuite attributes
    testsuite.set("failures", str(failures))
    testsuite.set("errors", str(errors))
    testsuite.set("skipped", "0")
    
    # Write XML to file
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
