# Changelog

All notable changes to Engram will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-01-02

### Added
- Initial release of Engram
- PostgreSQL + pgvector for semantic memory storage
- pgvector for semantic search
- MCP server for Claude Code integration
- REST API for memory operations
- Auto-capture hooks for conversations
- OpenTelemetry support for tracing (optional)
- Docker Compose setup for local deployment
- MemoryML specification (draft)

### MCP Tools
- `add_coding_preference` - Store memories
- `search_coding_preferences` - Semantic search
- `get_all_coding_preferences` - List memories
- `link_memories` - Connect memories
- `get_related_memories` - Graph traversal
- `analyze_memory_intelligence` - Health reports

[Unreleased]: https://github.com/agents-squads/engram/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/agents-squads/engram/releases/tag/v0.1.0
