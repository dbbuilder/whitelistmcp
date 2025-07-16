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

# Check git
Write-Host "Checking git..." -ForegroundColor Green
try {
    $gitVersion = git --version
    Write-Host "✓ $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: git not found. Please install git from https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# Set installation directory
$installDir = "$env:USERPROFILE\.awswhitelist-mcp"

# Clone or update repository
Write-Host ""
if (Test-Path $installDir) {
    Write-Host "Updating existing installation..." -ForegroundColor Green
    Push-Location $installDir
    git pull
    Pop-Location
} else {
    Write-Host "Cloning repository..." -ForegroundColor Green
    git clone https://github.com/dbbuilder/awswhitelist2.git $installDir
}

# Install Python package
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Green
Push-Location $installDir
python -m pip install -e . --user
Pop-Location

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
    command = "python"
    args = @("-m", "awswhitelist.main")
    cwd = $installDir.Replace('\', '/')
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
Push-Location $installDir
try {
    $testOutput = python -m awswhitelist.main --help 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Installation test passed" -ForegroundColor Green
    } else {
        Write-Host "Warning: Installation test failed. Please check the error messages above." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Warning: Could not test installation." -ForegroundColor Yellow
}
Pop-Location

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
Write-Host "  cd $installDir"
Write-Host "  python -m awswhitelist.main --help"
Write-Host ""
Write-Host "Configuration file location:" -ForegroundColor Yellow
Write-Host "  $configPath"
Write-Host ""