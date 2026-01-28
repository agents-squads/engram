"""
Pytest configuration for Engram tests.

Note: Shell-based integration tests (test_*.sh) require Docker stack running.
Python tests here are for unit tests and CI validation.
"""
import os

import pytest


@pytest.fixture
def test_env():
    """Set up test environment variables."""
    return {
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL",
            "postgresql://engram:engram@localhost:5432/engram"
        ),
        "TESTING": "true",
    }
