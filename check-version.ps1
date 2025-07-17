# Check awswhitelist version and update from PyPI
Write-Host "Checking awswhitelist installation..." -ForegroundColor Cyan
Write-Host ""

# Check if command exists
Write-Host "1. Checking if awswhitelist command is available:" -ForegroundColor Yellow
$cmdFound = $false
try {
    $cmdPath = (Get-Command awswhitelist -ErrorAction Stop).Source
    Write-Host "   Found at: $cmdPath" -ForegroundColor Green
    $cmdFound = $true
} catch {
    Write-Host "   Command not found in PATH" -ForegroundColor Red
    Write-Host "   Looking for Python Scripts directory..." -ForegroundColor Yellow
}

if (-not $cmdFound) {
    # Try to find Python Scripts directory
    try {
        $pythonPath = (Get-Command python -ErrorAction Stop).Source
        $scriptsPath = Join-Path (Split-Path (Split-Path $pythonPath)) "Scripts"
        $awswhitelistPath = Join-Path $scriptsPath "awswhitelist.exe"
        if (Test-Path $awswhitelistPath) {
            Write-Host "   Found at: $awswhitelistPath" -ForegroundColor Green
            Write-Host "   Add this to your PATH: $scriptsPath" -ForegroundColor Yellow
        } else {
            Write-Host "   Not found in Python Scripts directory" -ForegroundColor Red
        }
    } catch {
        Write-Host "   Could not locate Python installation" -ForegroundColor Red
    }
}

# Check installed package version
Write-Host ""
Write-Host "2. Checking installed package version:" -ForegroundColor Yellow
try {
    $pipShow = python -m pip show awswhitelist_mcp 2>&1
    if ($LASTEXITCODE -eq 0) {
        $versionLine = $pipShow | Select-String "Version:"
        $locationLine = $pipShow | Select-String "Location:"
        
        if ($versionLine) {
            $version = $versionLine.ToString().Split()[1]
            Write-Host "   Package: awswhitelist_mcp" -ForegroundColor Green
            Write-Host "   Version: $version" -ForegroundColor Green
        }
        
        if ($locationLine) {
            $location = $locationLine.ToString().Split()[1]
            Write-Host "   Location: $location" -ForegroundColor Green
        }
    } else {
        Write-Host "   Package not installed" -ForegroundColor Red
    }
} catch {
    Write-Host "   Error checking package: $_" -ForegroundColor Red
}

# Check for updates
Write-Host ""
Write-Host "3. Checking for updates from PyPI:" -ForegroundColor Yellow
try {
    $pipList = python -m pip list --outdated 2>&1 | Select-String "awswhitelist"
    if ($pipList) {
        Write-Host "   Update available!" -ForegroundColor Yellow
        Write-Host "   $pipList" -ForegroundColor Yellow
    } else {
        Write-Host "   Package is up to date" -ForegroundColor Green
    }
} catch {
    Write-Host "   Could not check for updates" -ForegroundColor Yellow
}

# Provide update commands
Write-Host ""
Write-Host "4. Update commands:" -ForegroundColor Yellow
Write-Host "   To update to latest version:" -ForegroundColor Cyan
Write-Host "   python -m pip install --upgrade awswhitelist_mcp" -ForegroundColor White
Write-Host ""
Write-Host "   To force reinstall:" -ForegroundColor Cyan
Write-Host "   python -m pip install --upgrade --force-reinstall awswhitelist_mcp" -ForegroundColor White
Write-Host ""
Write-Host "   To uninstall and reinstall:" -ForegroundColor Cyan
Write-Host "   python -m pip uninstall awswhitelist_mcp -y" -ForegroundColor White
Write-Host "   python -m pip install awswhitelist_mcp" -ForegroundColor White

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan