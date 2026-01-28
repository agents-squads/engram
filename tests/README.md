# Engram Tests

## Test Types

### Python Tests (pytest)
- `conftest.py` - Shared fixtures
- `test_imports.py` - Package import validation

Run with:
```bash
pytest tests/ -v
```

### Shell Integration Tests
These require the full Docker stack running:
- `test_api.sh` - API endpoint tests
- `test_auth.sh` - Authentication tests
- `test_mcp.sh` - MCP protocol tests
- `test_integration.sh` - End-to-end tests
- `test_memory_*.sh` - Memory system tests
- `test_ownership*.sh` - Ownership/isolation tests

Run with:
```bash
./scripts/start.sh  # Start Docker stack first
./tests/test_api.sh
```

## CI Pipeline

The CI runs:
1. **pytest** - Python unit tests (validates imports and environment)
2. **Docker build** - Verifies images build correctly
3. **ruff lint** - Code quality checks

Shell integration tests run locally with Docker stack.
