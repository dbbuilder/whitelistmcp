#!/bin/bash
set -e

echo "Installing AWS Whitelisting MCP Server..."

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

# Clone or update repository
if [ -d "$HOME/.awswhitelist-mcp" ]; then
    echo "Updating existing installation..."
    cd "$HOME/.awswhitelist-mcp"
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/dbbuilder/awswhitelist2.git "$HOME/.awswhitelist-mcp"
    cd "$HOME/.awswhitelist-mcp"
fi

# Install package
echo "Installing Python package..."
pip3 install -e . --user

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

config['mcpServers']['awswhitelist'] = {
    'command': 'python3',
    'args': ['-m', 'awswhitelist.main'],
    'cwd': '$HOME/.awswhitelist-mcp',
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
    "awswhitelist": {
      "command": "python3",
      "args": ["-m", "awswhitelist.main"],
      "cwd": "$HOME/.awswhitelist-mcp",
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
echo "2. The AWS Whitelisting server will be available in Claude"
echo ""
echo "To test the installation:"
echo "  cd $HOME/.awswhitelist-mcp"
echo "  python3 -m awswhitelist.main --help"
echo ""