# Packaging and Distribution Guide

This guide covers how to package and distribute the AWS Whitelisting MCP Server for easy third-party use.

## Distribution Options

### 1. PyPI (Python Package Index) - Recommended

#### Setup for PyPI

1. **Update setup.py** for PyPI compatibility:
   ```python
   setup(
       name="awswhitelist-mcp",
       version="1.0.0",
       author="Your Name",
       author_email="your.email@example.com",
       description="MCP server for AWS Security Group IP whitelisting",
       long_description=open("README.md").read(),
       long_description_content_type="text/markdown",
       url="https://github.com/dbbuilder/awswhitelist2",
       packages=find_packages(),
       classifiers=[
           "Programming Language :: Python :: 3",
           "License :: OSI Approved :: MIT License",
           "Operating System :: OS Independent",
       ],
       python_requires=">=3.8",
       install_requires=[
           "boto3>=1.26.0",
           "pydantic>=2.0.0",
           "python-dateutil>=2.8.0",
           "requests>=2.28.0",
           "pythonjsonlogger>=2.0.0",
       ],
       entry_points={
           "console_scripts": [
               "awswhitelist=awswhitelist.main:main",
           ],
       },
   )
   ```

2. **Build and upload**:
   ```bash
   # Install build tools
   pip install build twine

   # Build the package
   python -m build

   # Upload to PyPI
   python -m twine upload dist/*
   ```

3. **Users can then install with**:
   ```bash
   pip install awswhitelist-mcp
   ```

### 2. GitHub Releases with Installers

#### Create release artifacts:

1. **Python wheel**:
   ```bash
   python -m build --wheel
   ```

2. **Standalone executable (using PyInstaller)**:
   ```bash
   pip install pyinstaller
   pyinstaller --onefile --name awswhitelist awswhitelist/main.py
   ```

3. **Docker image**:
   ```bash
   docker build -t awswhitelist-mcp .
   docker save awswhitelist-mcp > awswhitelist-mcp.tar
   ```

4. **Create GitHub Release**:
   ```bash
   gh release create v1.0.0 \
     dist/*.whl \
     dist/awswhitelist \
     awswhitelist-mcp.tar \
     --title "AWS Whitelisting MCP Server v1.0.0" \
     --notes "First stable release"
   ```

### 3. MCP Server Registry

Register with the official MCP server registry (when available):

1. Create `mcp-server.json`:
   ```json
   {
     "name": "awswhitelist",
     "version": "1.0.0",
     "description": "AWS Security Group IP whitelisting",
     "author": "Your Name",
     "repository": "https://github.com/dbbuilder/awswhitelist2",
     "homepage": "https://github.com/dbbuilder/awswhitelist2",
     "license": "MIT",
     "runtime": "python",
     "install": {
       "pip": "awswhitelist-mcp"
     },
     "configuration": {
       "command": "awswhitelist",
       "args": [],
       "env": {
         "PYTHONUNBUFFERED": "1"
       }
     },
     "methods": [
       "whitelist/add",
       "whitelist/remove",
       "whitelist/list",
       "whitelist/check"
     ]
   }
   ```

### 4. One-Click Installation Scripts

#### For Windows:
Create `install-windows.ps1`:
```powershell
# Install AWS Whitelisting MCP Server
Write-Host "Installing AWS Whitelisting MCP Server..." -ForegroundColor Green

# Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

# Install package
pip install awswhitelist-mcp

# Configure Claude Desktop
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$config = @{
    mcpServers = @{
        awswhitelist = @{
            command = "awswhitelist"
            args = @()
            env = @{
                PYTHONUNBUFFERED = "1"
            }
        }
    }
}

# Create or update config
if (Test-Path $configPath) {
    $existing = Get-Content $configPath | ConvertFrom-Json
    $existing.mcpServers.awswhitelist = $config.mcpServers.awswhitelist
    $existing | ConvertTo-Json -Depth 10 | Set-Content $configPath
} else {
    New-Item -ItemType Directory -Path (Split-Path $configPath) -Force
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath
}

Write-Host "Installation complete! Restart Claude Desktop to use the server." -ForegroundColor Green
```

#### For macOS/Linux:
Create `install.sh`:
```bash
#!/bin/bash
set -e

echo "Installing AWS Whitelisting MCP Server..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Install package
pip3 install awswhitelist-mcp

# Configure Claude Desktop
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
    CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
fi

# Create config directory
mkdir -p "$(dirname "$CONFIG_PATH")"

# Add MCP server config
if [ -f "$CONFIG_PATH" ]; then
    # Update existing config
    python3 -c "
import json
with open('$CONFIG_PATH', 'r') as f:
    config = json.load(f)
if 'mcpServers' not in config:
    config['mcpServers'] = {}
config['mcpServers']['awswhitelist'] = {
    'command': 'awswhitelist',
    'args': [],
    'env': {'PYTHONUNBUFFERED': '1'}
}
with open('$CONFIG_PATH', 'w') as f:
    json.dump(config, f, indent=2)
"
else
    # Create new config
    cat > "$CONFIG_PATH" << EOF
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": [],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
EOF
fi

echo "Installation complete! Restart Claude Desktop to use the server."
```

### 5. GitHub Template Repository

Create a template repository that users can clone:

1. **Add `.github/ISSUE_TEMPLATE/`** for bug reports
2. **Add `.github/workflows/`** for CI/CD
3. **Include comprehensive examples**
4. **Add `CONTRIBUTING.md`**

### 6. Docker Hub

Publish to Docker Hub for easy deployment:

```bash
# Build and tag
docker build -t yourusername/awswhitelist-mcp:latest .

# Push to Docker Hub
docker push yourusername/awswhitelist-mcp:latest

# Users can then run:
docker run -i yourusername/awswhitelist-mcp:latest
```

## Quick Start for End Users

After packaging, users should be able to install with:

### Option 1: pip (Simplest)
```bash
pip install awswhitelist-mcp
```

### Option 2: One-line installer
```bash
# macOS/Linux
curl -sSL https://raw.githubusercontent.com/dbbuilder/awswhitelist2/main/install.sh | bash

# Windows PowerShell
iwr -useb https://raw.githubusercontent.com/dbbuilder/awswhitelist2/main/install-windows.ps1 | iex
```

### Option 3: Docker
```bash
docker run -i awswhitelist-mcp
```

## Publishing Checklist

- [ ] Update version in `setup.py`
- [ ] Update `CHANGELOG.md`
- [ ] Run all tests
- [ ] Build distribution packages
- [ ] Create GitHub release
- [ ] Upload to PyPI
- [ ] Update Docker Hub
- [ ] Update documentation
- [ ] Announce on relevant forums/communities

## Maintenance

1. **Semantic Versioning**: Use MAJOR.MINOR.PATCH
2. **Deprecation Policy**: Announce breaking changes one version ahead
3. **Security Updates**: Publish security fixes immediately
4. **Compatibility**: Test with multiple Python versions

## Integration with Package Managers

### Homebrew (macOS)
Create a formula:
```ruby
class AwswhitelistMcp < Formula
  desc "MCP server for AWS Security Group IP whitelisting"
  homepage "https://github.com/dbbuilder/awswhitelist2"
  url "https://github.com/dbbuilder/awswhitelist2/archive/v1.0.0.tar.gz"
  sha256 "..."
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end
end
```

### Chocolatey (Windows)
Create a package:
```xml
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd">
  <metadata>
    <id>awswhitelist-mcp</id>
    <version>1.0.0</version>
    <title>AWS Whitelisting MCP Server</title>
    <authors>Your Name</authors>
    <projectUrl>https://github.com/dbbuilder/awswhitelist2</projectUrl>
    <description>MCP server for AWS Security Group IP whitelisting</description>
  </metadata>
</package>
```