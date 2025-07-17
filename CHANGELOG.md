# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-07-17

### Fixed
- Fixed MCP compliance by redirecting all logging output to stderr
- Log messages no longer interfere with JSON-RPC communication on stdout
- Fixed print statements in config.py to use stderr
- Resolved "invalid literal value, expected 2.0" errors in Claude Desktop

### Changed
- Updated .gitignore to exclude claude_desktop*.json files
- Improved Windows PowerShell installer for better JSON handling

## [1.0.0] - 2025-07-16

### Added
- Initial release of AWS Whitelisting MCP Server
- Support for adding, removing, listing, and checking IP whitelist rules
- Stateless credential handling (no credential storage)
- MCP protocol implementation with JSON-RPC 2.0
- Comprehensive test suite with 91 tests
- Docker support with security hardening
- Platform-specific installation scripts
- Claude Desktop integration