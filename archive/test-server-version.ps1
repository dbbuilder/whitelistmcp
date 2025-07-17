# Quick test to check awswhitelist MCP server version
param(
    [string]$Command = "awswhitelist"
)

Write-Host "Testing awswhitelist MCP server..." -ForegroundColor Cyan

# Create test request
$initRequest = @{
    jsonrpc = "2.0"
    method = "initialize"
    params = @{}
    id = 1
} | ConvertTo-Json -Compress

# Run the command
$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = $Command
$pinfo.RedirectStandardInput = $true
$pinfo.RedirectStandardOutput = $true
$pinfo.RedirectStandardError = $true
$pinfo.UseShellExecute = $false
$pinfo.CreateNoWindow = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $pinfo

try {
    $started = $p.Start()
    if (-not $started) {
        throw "Failed to start process"
    }
    
    $p.StandardInput.WriteLine($initRequest)
    $p.StandardInput.Close()
    
    # Wait for response
    $timeout = 2000
    $output = ""
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    
    while ($sw.ElapsedMilliseconds -lt $timeout -and -not $p.HasExited) {
        if ($p.StandardOutput.Peek() -ge 0) {
            $output = $p.StandardOutput.ReadLine()
            if ($output) { break }
        }
        Start-Sleep -Milliseconds 50
    }
    
    if (-not $p.HasExited) { 
        $p.Kill() 
    }
    
    if ($output) {
        try {
            $response = $output | ConvertFrom-Json
            if ($response.result) {
                Write-Host "SUCCESS - Server responded" -ForegroundColor Green
                Write-Host "  Protocol: $($response.result.protocolVersion)" -ForegroundColor Gray
                Write-Host "  Server: $($response.result.serverInfo.name)" -ForegroundColor Gray
                Write-Host "  Version: $($response.result.serverInfo.version)" -ForegroundColor Gray
            }
            elseif ($response.error) {
                Write-Host "ERROR - Server returned error" -ForegroundColor Red
                Write-Host "  Code: $($response.error.code)" -ForegroundColor Red
                Write-Host "  Message: $($response.error.message)" -ForegroundColor Red
            }
        }
        catch {
            Write-Host "ERROR - Failed to parse response: $_" -ForegroundColor Red
            Write-Host "  Raw output: $output" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "ERROR - No response from server" -ForegroundColor Red
        
        # Check stderr for errors
        try {
            $errors = $p.StandardError.ReadToEnd()
            if ($errors) {
                Write-Host "  Error output:" -ForegroundColor Red
                Write-Host $errors -ForegroundColor Gray
            }
        }
        catch {
            # Ignore errors reading stderr
        }
    }
}
catch {
    Write-Host "ERROR - Failed to run command: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure awswhitelist is installed:" -ForegroundColor Yellow
    Write-Host "  python -m pip install --upgrade awswhitelist_mcp" -ForegroundColor White
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan