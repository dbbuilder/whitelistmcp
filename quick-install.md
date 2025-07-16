# Quick Installation

## One-line installers

### macOS/Linux:
```bash
curl -sSL https://raw.githubusercontent.com/dbbuilder/awswhitelist2/main/install.sh | bash
```

### Windows PowerShell (Run as Administrator):
```powershell
iwr -useb https://raw.githubusercontent.com/dbbuilder/awswhitelist2/main/install-windows.ps1 | iex
```

## What the installer does:

1. Checks for Python 3.8+ and git
2. Clones the repository to `~/.awswhitelist-mcp`
3. Installs the Python package
4. Configures Claude Desktop automatically
5. Tests the installation

## Manual installation:

If you prefer to install manually, see [CLAUDE_DESKTOP_SETUP.md](CLAUDE_DESKTOP_SETUP.md)