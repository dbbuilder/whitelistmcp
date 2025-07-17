# Test JSON output from awswhitelist
Write-Host "Testing awswhitelist JSON output..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Simple initialize request
Write-Host "Test 1: Initialize request via pipe" -ForegroundColor Yellow
$initRequest = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

# Create temp file with request
$tempFile = New-TemporaryFile
Set-Content -Path $tempFile -Value $initRequest

# Run command and capture output
$output = Get-Content $tempFile | & "C:\Python312\Scripts\awswhitelist.exe" 2>&1 | Out-String

Write-Host "Output:" -ForegroundColor Green
Write-Host $output

# Clean up
Remove-Item $tempFile -Force

# Test 2: Direct Python test
Write-Host ""
Write-Host "Test 2: Direct Python test of server" -ForegroundColor Yellow

$pythonScript = @'
import sys
import json
sys.path.insert(0, r"D:\dev2\awswhitelist2")
try:
    from awswhitelist.main import MCPServer
    server = MCPServer()
    request = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'
    response = server.process_request(request)
    print(f"Response: {response}")
    try:
        parsed = json.loads(response)
        print("Valid JSON: Yes")
        print(f"Has result: {'result' in parsed}")
        print(f"Has error: {'error' in parsed}")
        if 'result' in parsed and 'serverInfo' in parsed['result']:
            print(f"Server version: {parsed['result']['serverInfo']['version']}")
    except Exception as e:
        print(f"JSON Parse Error: {e}")
except Exception as e:
    print(f"Import/Run Error: {e}")
    import traceback
    traceback.print_exc()
'@

$pythonScript | python -

Write-Host ""
Write-Host "Test 3: Check what's in Scripts directory" -ForegroundColor Yellow
Get-ChildItem "C:\Python312\Scripts\awswhitelist*" | ForEach-Object {
    Write-Host "  $($_.Name) - $($_.Length) bytes - $($_.LastWriteTime)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan