# AWS Whitelisting MCP Server Installer for Windows
Write-Host "AWS Whitelisting MCP Server - Windows Installer" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin rights (not required but recommended)
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Note: Running without administrator privileges. Installation will proceed for current user only." -ForegroundColor Yellow
    Write-Host ""
}

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
            Write-Host "Error: Python 3.8+ required. Found: $pythonVersion" -ForegroundColor Red
            exit 1
        }
        Write-Host "✓ Found $pythonVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "Error: Python not found. Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Check pip
Write-Host "Checking pip..." -ForegroundColor Green
try {
    $pipVersion = python -m pip --version
    Write-Host "✓ pip is available" -ForegroundColor Green
} catch {
    Write-Host "Error: pip not found. Please ensure pip is installed with Python." -ForegroundColor Red
    exit 1
}


# Install from PyPI
Write-Host ""
Write-Host "Installing AWS Whitelisting MCP Server from PyPI..." -ForegroundColor Green
python -m pip install --user awswhitelist-mcp

# Configure Claude Desktop
Write-Host ""
Write-Host "Configuring Claude Desktop..." -ForegroundColor Green

$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$configDir = Split-Path $configPath -Parent

# Create directory if it doesn't exist
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Prepare MCP server configuration
$mcpConfig = @{
    command = "awswhitelist"
    args = @()
    env = @{
        PYTHONUNBUFFERED = "1"
    }
}

# Load or create configuration
if (Test-Path $configPath) {
    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        if (-not $config.mcpServers) {
            $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{} -Force
        }
    } catch {
        Write-Host "Warning: Existing config file is invalid. Creating new configuration." -ForegroundColor Yellow
        $config = @{ mcpServers = @{} }
    }
} else {
    $config = @{ mcpServers = @{} }
}

# Add or update awswhitelist server
$config.mcpServers.awswhitelist = $mcpConfig

# Save configuration
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8

Write-Host "✓ Configuration saved to: $configPath" -ForegroundColor Green

# Test installation
Write-Host ""
Write-Host "Testing installation..." -ForegroundColor Green
$testError = $null
try {
    $testOutput = awswhitelist --help 2>&1
    Write-Host "✓ Installation test passed" -ForegroundColor Green
}
catch {
    Write-Host "Warning: Could not test installation. Error: $_" -ForegroundColor Yellow
}

# Final instructions
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "✅ Installation complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart Claude Desktop application"
Write-Host "2. The AWS Whitelisting server will be available in Claude"
Write-Host ""
Write-Host "To manually test the server:" -ForegroundColor Yellow
Write-Host "  awswhitelist --help"
Write-Host ""
Write-Host "Configuration file location:" -ForegroundColor Yellow
Write-Host "  $configPath"
Write-Host ""