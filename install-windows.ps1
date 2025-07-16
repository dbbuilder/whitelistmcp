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
$pythonInstalled = $false
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
            Write-Host "Error: Python 3.8+ required. Found: $pythonVersion" -ForegroundColor Red
            exit 1
        }
        Write-Host "Found $pythonVersion" -ForegroundColor Green
        $pythonInstalled = $true
    }
}
catch {
    Write-Host "Error: Python not found. Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

if (-not $pythonInstalled) {
    Write-Host "Error: Could not verify Python installation" -ForegroundColor Red
    exit 1
}

# Check pip
Write-Host "Checking pip..." -ForegroundColor Green
$pipInstalled = $false
try {
    $pipVersion = python -m pip --version 2>&1
    if ($pipVersion -match "pip") {
        Write-Host "pip is available" -ForegroundColor Green
        $pipInstalled = $true
    }
}
catch {
    Write-Host "Error: pip not found. Please ensure pip is installed with Python." -ForegroundColor Red
    exit 1
}

if (-not $pipInstalled) {
    Write-Host "Error: Could not verify pip installation" -ForegroundColor Red
    exit 1
}

# Install from PyPI
Write-Host ""
Write-Host "Installing AWS Whitelisting MCP Server from PyPI..." -ForegroundColor Green
$installResult = python -m pip install --user awswhitelist-mcp 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Package installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Error installing package. Output:" -ForegroundColor Red
    Write-Host $installResult
    exit 1
}

# Configure Claude Desktop
Write-Host ""
Write-Host "Configuring Claude Desktop..." -ForegroundColor Green

$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$configDir = Split-Path $configPath -Parent

# Create directory if it doesn't exist
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Load or create configuration
if (Test-Path $configPath) {
    try {
        $configContent = Get-Content $configPath -Raw
        # Parse existing JSON (compatible with older PowerShell)
        $config = $configContent | ConvertFrom-Json
        
        # Ensure mcpServers exists
        if (-not $config.mcpServers) {
            $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{}) -Force
        }
        
        # Create awswhitelist configuration
        $awsConfig = [PSCustomObject]@{
            command = "awswhitelist"
            args = @()
            env = [PSCustomObject]@{
                PYTHONUNBUFFERED = "1"
            }
        }
        
        # Add awswhitelist to mcpServers
        if ($config.mcpServers -is [PSCustomObject]) {
            $config.mcpServers | Add-Member -MemberType NoteProperty -Name "awswhitelist" -Value $awsConfig -Force
        }
        
        # Convert to JSON with proper formatting
        $jsonOutput = $config | ConvertTo-Json -Depth 10
        
        # Write the JSON file
        Set-Content -Path $configPath -Value $jsonOutput -Encoding UTF8
        Write-Host "Configuration saved to: $configPath" -ForegroundColor Green
    }
    catch {
        Write-Host "Error updating configuration: $_" -ForegroundColor Red
        Write-Host "Please check your Claude Desktop config file for syntax errors." -ForegroundColor Yellow
        exit 1
    }
} else {
    # Create new configuration
    $config = [PSCustomObject]@{
        mcpServers = [PSCustomObject]@{
            awswhitelist = [PSCustomObject]@{
                command = "awswhitelist"
                args = @()
                env = [PSCustomObject]@{
                    PYTHONUNBUFFERED = "1"
                }
            }
        }
    }
    
    try {
        $jsonOutput = $config | ConvertTo-Json -Depth 10
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
        Set-Content -Path $configPath -Value $jsonOutput -Encoding UTF8
        Write-Host "Configuration created at: $configPath" -ForegroundColor Green
    }
    catch {
        Write-Host "Error creating configuration: $_" -ForegroundColor Red
        exit 1
    }
}

# Test installation
Write-Host ""
Write-Host "Testing installation..." -ForegroundColor Green
$testResult = $null
try {
    $testResult = cmd /c "awswhitelist --help 2>&1"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installation test passed!" -ForegroundColor Green
    } else {
        Write-Host "Warning: Could not verify installation. You may need to restart your terminal." -ForegroundColor Yellow
    }
}
catch {
    Write-Host "Warning: Could not test installation. You may need to restart your terminal." -ForegroundColor Yellow
}

# Final instructions
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart Claude Desktop application" -ForegroundColor White
Write-Host "2. The AWS Whitelisting server will be available in Claude" -ForegroundColor White
Write-Host ""
Write-Host "To manually test the server:" -ForegroundColor Yellow
Write-Host "  awswhitelist --help" -ForegroundColor White
Write-Host ""
Write-Host "Configuration file location:" -ForegroundColor Yellow
Write-Host "  $configPath" -ForegroundColor White
Write-Host ""