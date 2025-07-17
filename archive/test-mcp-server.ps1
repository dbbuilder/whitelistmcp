# Test MCP server and capture stderr
$testRequest = @'
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}
'@

Write-Host "Testing awswhitelist MCP server..." -ForegroundColor Green

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
Start-Sleep -Milliseconds 500

# Read output
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()

# Clean up
if (!$process.HasExited) {
    $process.Kill()
}

Write-Host "`nSTDOUT:" -ForegroundColor Yellow
Write-Host $stdout

Write-Host "`nSTDERR (Error messages):" -ForegroundColor Red
Write-Host $stderr

Write-Host "`nExit Code:" $process.ExitCode -ForegroundColor Cyan