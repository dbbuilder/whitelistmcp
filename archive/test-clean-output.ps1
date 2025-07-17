# Test clean output from awswhitelist
Write-Host "Testing clean awswhitelist output..." -ForegroundColor Cyan
Write-Host ""

$initRequest = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

# Test 1: Raw output test
Write-Host "Test 1: Raw output (should be ONLY JSON-RPC response)" -ForegroundColor Yellow
$tempFile = New-TemporaryFile
Set-Content -Path $tempFile -Value $initRequest

$process = Start-Process -FilePath "C:\Python312\Scripts\awswhitelist.exe" `
    -RedirectStandardInput -RedirectStandardOutput -RedirectStandardError `
    -NoNewWindow -PassThru

# Send input
$fileContent = Get-Content $tempFile -Raw
$process.StandardInput.WriteLine($fileContent.Trim())
$process.StandardInput.Close()

# Wait for output
Start-Sleep -Milliseconds 500

# Get output
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()

if (-not $process.HasExited) {
    $process.Kill()
}

Write-Host "STDOUT:" -ForegroundColor Green
Write-Host $stdout
Write-Host ""
Write-Host "STDERR:" -ForegroundColor Yellow  
Write-Host $stderr

# Validate JSON
Write-Host ""
Write-Host "Validation:" -ForegroundColor Cyan
try {
    $json = $stdout | ConvertFrom-Json
    Write-Host "✓ Valid JSON" -ForegroundColor Green
    Write-Host "✓ Has jsonrpc: $($json.jsonrpc)" -ForegroundColor Green
    Write-Host "✓ Has id: $($json.id)" -ForegroundColor Green
    Write-Host "✓ Has result: $($null -ne $json.result)" -ForegroundColor Green
    if ($json.result.serverInfo) {
        Write-Host "✓ Server version: $($json.result.serverInfo.version)" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Invalid JSON: $_" -ForegroundColor Red
}

Remove-Item $tempFile -Force

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan