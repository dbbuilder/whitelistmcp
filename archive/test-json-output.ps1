# Test JSON output from awswhitelist
Write-Host "Testing awswhitelist JSON output..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Simple initialize request
Write-Host "Test 1: Initialize request" -ForegroundColor Yellow
$initRequest = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

$process = Start-Process -FilePath "C:\Python312\Scripts\awswhitelist.exe" -NoNewWindow -RedirectStandardInput -RedirectStandardOutput -RedirectStandardError -PassThru
$process.StandardInput.WriteLine($initRequest)
$process.StandardInput.Close()

Start-Sleep -Seconds 2

$stdout = ""
$stderr = ""

if ($process.StandardOutput.Peek() -ge 0) {
    $stdout = $process.StandardOutput.ReadToEnd()
}

if ($process.StandardError.Peek() -ge 0) {
    $stderr = $process.StandardError.ReadToEnd()
}

if (-not $process.HasExited) {
    $process.Kill()
}

Write-Host "STDOUT (should be JSON):" -ForegroundColor Green
Write-Host $stdout
Write-Host ""

Write-Host "STDERR (should be logs only):" -ForegroundColor Yellow
Write-Host $stderr
Write-Host ""

# Check if stdout is valid JSON
try {
    $json = $stdout | ConvertFrom-Json
    Write-Host "✓ Valid JSON output" -ForegroundColor Green
} catch {
    Write-Host "✗ Invalid JSON output: $_" -ForegroundColor Red
}

# Test 2: Check if logging is going to stdout
Write-Host ""
Write-Host "Test 2: Check for stdout pollution" -ForegroundColor Yellow

$testCmd = @"
import sys
sys.path.insert(0, r'D:\dev2\awswhitelist2')
from awswhitelist.main import main
print("TESTING STDOUT", file=sys.stdout)
print("TESTING STDERR", file=sys.stderr)
"@

$testCmd | python -

Write-Host ""
Write-Host "Test 3: Direct Python test" -ForegroundColor Yellow
$pythonTest = @"
import sys
import json
sys.path.insert(0, r'D:\dev2\awswhitelist2')
from awswhitelist.main import MCPServer

server = MCPServer()
request = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'
response = server.process_request(request)
print(f"Response: {response}")
print(f"Is valid JSON: {bool(json.loads(response))}")
"@

$pythonTest | python -

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan