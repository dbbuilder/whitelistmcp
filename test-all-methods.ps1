# Test all MCP methods for awswhitelist server
Write-Host "Testing awswhitelist MCP server methods..." -ForegroundColor Green

# Function to test a single method
function Test-MCPMethod {
    param(
        [string]$Method,
        [string]$RequestJson
    )
    
    Write-Host "`nTesting method: $Method" -ForegroundColor Yellow
    
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "awswhitelist"
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    
    try {
        $process.Start() | Out-Null
        $process.StandardInput.WriteLine($RequestJson)
        $process.StandardInput.Close()
        
        Start-Sleep -Milliseconds 500
        
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        
        if (!$process.HasExited) {
            $process.Kill()
        }
        
        # Parse and display response
        try {
            $response = $stdout | ConvertFrom-Json
            if ($response.result) {
                Write-Host "✓ SUCCESS" -ForegroundColor Green
                Write-Host "Result:" -ForegroundColor Cyan
                $response.result | ConvertTo-Json -Depth 5 | Write-Host
            } elseif ($response.error) {
                Write-Host "✗ ERROR" -ForegroundColor Red
                Write-Host "Error: $($response.error.message)" -ForegroundColor Red
            }
        } catch {
            Write-Host "✗ Failed to parse response" -ForegroundColor Red
            Write-Host "Raw output: $stdout" -ForegroundColor Gray
        }
        
    } catch {
        Write-Host "✗ Failed to run test: $_" -ForegroundColor Red
    }
}

# Test 1: Initialize
Test-MCPMethod "initialize" '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

# Test 2: Tools List
Test-MCPMethod "tools/list" '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'

# Test 3: Resources List
Test-MCPMethod "resources/list" '{"jsonrpc":"2.0","method":"resources/list","params":{},"id":3}'

# Test 4: Prompts List
Test-MCPMethod "prompts/list" '{"jsonrpc":"2.0","method":"prompts/list","params":{},"id":4}'

# Test 5: Notification (no response expected)
Write-Host "`nTesting notification: notifications/initialized" -ForegroundColor Yellow
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "awswhitelist"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
$process.Start() | Out-Null

# Send notification (no id field)
$process.StandardInput.WriteLine('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}')
$process.StandardInput.Close()

Start-Sleep -Milliseconds 500

$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()

if (!$process.HasExited) {
    $process.Kill()
}

if ([string]::IsNullOrWhiteSpace($stdout)) {
    Write-Host "✓ SUCCESS - No response for notification (expected)" -ForegroundColor Green
} else {
    Write-Host "✗ ERROR - Unexpected response for notification: $stdout" -ForegroundColor Red
}

Write-Host "`nAll tests completed!" -ForegroundColor Green