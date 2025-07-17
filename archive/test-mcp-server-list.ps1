# Test MCP server with a supported method
$testRequest = @'
{"jsonrpc":"2.0","method":"whitelist/list","params":{"credentials":{"access_key_id":"test","secret_access_key":"test","region":"us-east-1"},"security_group_id":"sg-test"},"id":"test-1"}
'@

Write-Host "Testing awswhitelist MCP server with whitelist/list method..." -ForegroundColor Green

# Create a process to capture both stdout and stderr
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "awswhitelist"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

# Start the process
$process.Start() | Out-Null

# Send test request
$process.StandardInput.WriteLine($testRequest)
$process.StandardInput.Close()

# Wait a moment for response
Start-Sleep -Milliseconds 1000

# Read output
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()

# Clean up
if (!$process.HasExited) {
    $process.Kill()
}

Write-Host "`nSTDOUT (JSON Response):" -ForegroundColor Yellow
Write-Host $stdout

Write-Host "`nSTDERR (Log messages):" -ForegroundColor Cyan
Write-Host $stderr

Write-Host "`nExit Code:" $process.ExitCode -ForegroundColor Green

# Parse and pretty print the JSON response if possible
try {
    $response = $stdout | ConvertFrom-Json
    Write-Host "`nParsed Response:" -ForegroundColor Magenta
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Could not parse JSON response" -ForegroundColor Red
}