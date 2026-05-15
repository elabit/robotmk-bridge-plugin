"""Test data generator for robotmk-bridge-plugin.

This module generates realistic test result files for different handler types
(JUnit, ZAP, Gatling). Used by both e2e tests and unit test fixtures.
"""

from .generator import (
    generate_all_handler_files,
    generate_handler_file,
    get_supported_handlers,
)

__all__ = [
    "generate_all_handler_files",
    "generate_handler_file",
    "get_supported_handlers",
]
