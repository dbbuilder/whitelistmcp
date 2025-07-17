# Debug script to find all awswhitelist installations
Write-Host "Debugging awswhitelist installations..." -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check all awswhitelist executables in PATH
Write-Host "1. Searching for awswhitelist in PATH:" -ForegroundColor Yellow
$allPaths = @()
try {
    $paths = where.exe awswhitelist 2>$null
    if ($paths) {
        $paths -split "`n" | ForEach-Object {
            $path = $_.Trim()
            if ($path) {
                Write-Host "   Found: $path" -ForegroundColor Green
                $allPaths += $path
            }
        }
    } else {
        Write-Host "   Not found in PATH" -ForegroundColor Red
    }
} catch {
    Write-Host "   Error searching PATH" -ForegroundColor Red
}

# 2. Check common Python installation locations
Write-Host ""
Write-Host "2. Checking common Python locations:" -ForegroundColor Yellow
$pythonLocations = @(
    "$env:LOCALAPPDATA\Programs\Python\Python*\Scripts",
    "$env:APPDATA\Python\Python*\Scripts",
    "C:\Python*\Scripts",
    "C:\Program Files\Python*\Scripts",
    "C:\Program Files (x86)\Python*\Scripts",
    "$env:USERPROFILE\AppData\Local\Programs\Python\Python*\Scripts",
    "$env:USERPROFILE\AppData\Roaming\Python\Python*\Scripts"
)

foreach ($pattern in $pythonLocations) {
    $dirs = Get-Item $pattern -ErrorAction SilentlyContinue
    foreach ($dir in $dirs) {
        $awsPath = Join-Path $dir "awswhitelist.exe"
        if (Test-Path $awsPath) {
            Write-Host "   Found: $awsPath" -ForegroundColor Green
            $allPaths += $awsPath
        }
    }
}

# 3. Check pip installations
Write-Host ""
Write-Host "3. Checking pip installations:" -ForegroundColor Yellow
try {
    # Check awswhitelist_mcp
    Write-Host "   Checking awswhitelist_mcp:" -ForegroundColor Cyan
    $result = python -m pip show awswhitelist_mcp 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = ($result | Select-String "Version:").ToString().Split()[1]
        $location = ($result | Select-String "Location:").ToString().Split()[1]
        Write-Host "     Version: $version" -ForegroundColor Green
        Write-Host "     Location: $location" -ForegroundColor Green
    } else {
        Write-Host "     Not installed" -ForegroundColor Red
    }
    
    # Check old package name
    Write-Host "   Checking awswhitelist-mcp (old name):" -ForegroundColor Cyan
    $result = python -m pip show awswhitelist-mcp 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = ($result | Select-String "Version:").ToString().Split()[1]
        $location = ($result | Select-String "Location:").ToString().Split()[1]
        Write-Host "     Version: $version" -ForegroundColor Yellow
        Write-Host "     Location: $location" -ForegroundColor Yellow
        Write-Host "     WARNING: Old package name installed!" -ForegroundColor Red
    } else {
        Write-Host "     Not installed (good)" -ForegroundColor Green
    }
} catch {
    Write-Host "   Error checking pip: $_" -ForegroundColor Red
}

# 4. Test each found executable
Write-Host ""
Write-Host "4. Testing each awswhitelist executable:" -ForegroundColor Yellow
$uniquePaths = $allPaths | Select-Object -Unique
foreach ($exePath in $uniquePaths) {
    Write-Host ""
    Write-Host "   Testing: $exePath" -ForegroundColor Cyan
    
    # Get file info
    try {
        $fileInfo = Get-Item $exePath
        Write-Host "     Modified: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
        Write-Host "     Size: $($fileInfo.Length) bytes" -ForegroundColor Gray
    } catch {}
    
    # Test initialize method
    try {
        $testRequest = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'
        
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = $exePath
        $pinfo.RedirectStandardInput = $true
        $pinfo.RedirectStandardOutput = $true
        $pinfo.RedirectStandardError = $true
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = $true
        
        $p = New-Object System.Diagnostics.Process
        $p.StartInfo = $pinfo
        
        if ($p.Start()) {
            $p.StandardInput.WriteLine($testRequest)
            $p.StandardInput.Close()
            
            $timeout = [System.Threading.Tasks.Task]::Run({
                Start-Sleep -Milliseconds 1000
            })
            
            $output = ""
            while (-not $timeout.IsCompleted -and -not $p.HasExited) {
                if ($p.StandardOutput.Peek() -ge 0) {
                    $line = $p.StandardOutput.ReadLine()
                    if ($line) {
                        $output = $line
                        break
                    }
                }
            }
            
            if (-not $p.HasExited) { $p.Kill() }
            
            if ($output) {
                try {
                    $response = $output | ConvertFrom-Json
                    if ($response.result -and $response.result.serverInfo) {
                        Write-Host "     Version: $($response.result.serverInfo.version)" -ForegroundColor Green
                        Write-Host "     Initialize: WORKS" -ForegroundColor Green
                    } elseif ($response.error) {
                        Write-Host "     Error: $($response.error.message)" -ForegroundColor Red
                        Write-Host "     Initialize: FAILS" -ForegroundColor Red
                    }
                } catch {
                    Write-Host "     Failed to parse response" -ForegroundColor Red
                }
            } else {
                Write-Host "     No response" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "     Failed to test: $_" -ForegroundColor Red
    }
}

# 5. Recommendations
Write-Host ""
Write-Host "5. Recommendations:" -ForegroundColor Yellow
Write-Host ""

# Check if old package is installed
$hasOldPackage = (python -m pip show awswhitelist-mcp 2>&1) -and ($LASTEXITCODE -eq 0)
if ($hasOldPackage) {
    Write-Host "   IMPORTANT: Uninstall the old package first:" -ForegroundColor Red
    Write-Host "   python -m pip uninstall awswhitelist-mcp -y" -ForegroundColor White
    Write-Host ""
}

Write-Host "   To ensure you have the latest version:" -ForegroundColor Cyan
Write-Host "   python -m pip install --upgrade --force-reinstall awswhitelist_mcp" -ForegroundColor White
Write-Host ""

Write-Host "   For Claude Desktop config, use the full path if needed:" -ForegroundColor Cyan
if ($uniquePaths.Count -gt 0) {
    $bestPath = $uniquePaths[0]
    Write-Host '   "awswhitelist": {' -ForegroundColor White
    Write-Host "       `"command`": `"$($bestPath -replace '\\', '\\')`"" -ForegroundColor White
    Write-Host '   }' -ForegroundColor White
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan