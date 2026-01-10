"""
Basic import tests to verify Python packages are correctly structured.

These tests ensure that CI can run pytest and core packages import correctly.
For full integration tests, use the shell scripts (test_*.sh) with Docker stack running.
"""
import pytest


class TestPackageImports:
    """Test that core packages can be imported."""

    def test_mem0_server_imports(self):
        """Test mem0-server core imports work."""
        # Note: mem0-server is structured as a standalone app, not a package
        # We verify that the dependencies are available
        import asyncpg
        import fastapi
        import pydantic

        assert asyncpg is not None
        assert fastapi is not None
        assert pydantic is not None

    def test_mcp_server_imports(self):
        """Test MCP server dependencies are available."""
        import httpx

        assert httpx is not None

    def test_cli_dependencies(self):
        """Test CLI script dependencies are available."""
        import click
        import tabulate

        assert click is not None
        assert tabulate is not None


class TestEnvironment:
    """Test environment configuration."""

    def test_testing_env_set(self, test_env):
        """Verify test environment is configured."""
        assert test_env["TESTING"] == "true"

    def test_database_url_configured(self, test_env):
        """Verify database URL is set."""
        assert "postgresql" in test_env["DATABASE_URL"]
