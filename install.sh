#!/bin/bash
set -e

echo "Installing Multi-Cloud Whitelisting MCP Server..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 not found. Please install pip3 first."
    exit 1
fi

# Install from PyPI
echo "Installing Multi-Cloud Whitelisting MCP Server from PyPI..."
pip3 install --user whitelistmcp

# Configure Claude Desktop
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
    CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
fi

# Create config directory
mkdir -p "$(dirname "$CONFIG_PATH")"

# Add MCP server config
echo "Configuring Claude Desktop..."
if [ -f "$CONFIG_PATH" ]; then
    # Update existing config
    python3 -c "
import json
import sys
config_path = '$CONFIG_PATH'
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['whitelistmcp'] = {
    'command': 'whitelistmcp',
    'args': [],
    'env': {'PYTHONUNBUFFERED': '1'}
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print('Configuration updated successfully!')
"
else
    # Create new config
    cat > "$CONFIG_PATH" << EOF
{
  "mcpServers": {
    "whitelistmcp": {
      "command": "whitelistmcp",
      "args": [],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
EOF
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Restart Claude Desktop"
echo "2. The Multi-Cloud Whitelisting server will be available in Claude"
echo ""
echo "To test the installation:"
echo "  whitelistmcp --help"
echo ""