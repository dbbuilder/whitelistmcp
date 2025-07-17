# Create a clean Claude Desktop config with proper encoding
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

Write-Host "Creating clean Claude Desktop configuration..." -ForegroundColor Green

# Define the clean configuration
$cleanConfig = @'
{
  "mcpServers": {
    "openmemory": {
      "command": "npx",
      "args": ["-y", "openmemory"],
      "env": {
        "OPENMEMORY_API_KEY": "om-hluci7jua30bj55jk9j378viyhe1hcpb",
        "CLIENT_NAME": "claude"
      }
    },
    "desktop-commander": {
      "command": "npx.cmd",
      "args": ["@wonderwhy-er/desktop-commander@latest"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
      }
    },
    "awswhitelist": {
      "command": "awswhitelist",
      "args": [],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  },
  "globalShortcut": "Shift+Alt+Ctrl+C"
}
'@

# Backup existing config if it exists
if (Test-Path $configPath) {
    $backupPath = "$configPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $configPath $backupPath
    Write-Host "Backed up existing config to: $backupPath" -ForegroundColor Yellow
}

# Create the directory if it doesn't exist
$configDir = Split-Path $configPath -Parent
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Write the file as UTF-8 without BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($configPath, $cleanConfig, $utf8NoBom)

Write-Host "Clean configuration created!" -ForegroundColor Green

# Verify the file
try {
    $test = Get-Content $configPath -Raw | ConvertFrom-Json
    Write-Host "JSON validation successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuration saved to: $configPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Restart Claude Desktop" -ForegroundColor White
    Write-Host "2. Check if all MCP servers load correctly" -ForegroundColor White
} catch {
    Write-Host "Error validating JSON: $_" -ForegroundColor Red
}