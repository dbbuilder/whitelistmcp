# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.5] - 2025-07-17

### Fixed
- **Critical**: Disabled console logging to ensure MCP protocol compliance
  - MCP servers must output ONLY JSON-RPC responses to stdout
  - Logging output was contaminating stdout causing "Unexpected end of JSON input" errors in Claude Desktop
  - Console logging is now completely disabled; use log files for debugging if needed
  - This fix ensures the server works correctly with Claude Desktop on Windows

### Notes
- Skipped version 1.1.4 to avoid confusion with internal testing versions

## [1.1.3] - 2025-07-17

### Changed
- Normalized package name from "awswhitelist-mcp" to "awswhitelist_mcp" for PEP 625 compliance
- This ensures the package name matches the generated wheel and tarball filenames

## [1.1.2] - 2025-07-17

### Added
- Implemented MCP protocol methods for full Claude Desktop compatibility:
  - `initialize` method returns server capabilities and version info
  - `tools/list` method returns available whitelist tools with schemas
  - `resources/list` method returns empty array (no resources provided)
  - `prompts/list` method returns empty array (no prompts provided)
- Added proper handling for MCP notifications (requests without id field)

### Changed
- Made MCPRequest id field optional to support notifications
- Updated serverInfo version to 1.1.2

## [1.1.1] - 2025-07-17

### Fixed
- **Critical**: Allow JSON-RPC id field to be either string or int per spec
  - Fixed Pydantic validation error that crashed server when receiving numeric IDs
  - MCPRequest and MCPResponse now accept Union[str, int] for id field
  - Resolves "server transport closed unexpectedly" error in Claude Desktop

### Changed
- Updated create_mcp_error function to accept Union[str, int] for request_id

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