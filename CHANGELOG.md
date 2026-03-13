# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

This project is licensed under AGPLv3.

## [0.11.1] - 2026-03-13

### Fixed
- **Critical crash fix**: `SQLiteStore` now uses thread-local connections (`threading.local()`)
  instead of a shared `self.conn`. This eliminates `EXC_BAD_ACCESS (SIGSEGV)` crashes that
  occurred when Inspector panel polling, Sync Worker background threads, and agent write
  operations accessed the same SQLite connection concurrently.
- Enabled WAL (Write-Ahead Logging) mode on all connections for better concurrent read/write
  performance without blocking.
- Verified fix with concurrent 6-thread stress test (2 writers + 3 readers + 1 inspector poller).

## [0.1.0] - 2026-03-06

### Added
- MemCell engine for structured memory units
- MemScene engine for scene-based containers
- Recall engine with tri-brain architecture (fast/mid/slow)
- Reconstructive recall for narrative generation
- Memory Pyramid with short/mid/long term tiers
- Skill engine (simplified) for experience-to-skill extraction
- Governance: conflict detection and version management
- Storage adapters: SQLite (default), base interface
- Python SDK with simple `Memory` API
- REST server for HTTP access
- 3 example demos: memory stress test, coding agent, research agent
- Docker support
