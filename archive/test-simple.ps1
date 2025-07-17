# Simple test to see what awswhitelist outputs
Write-Host "Simple awswhitelist test..." -ForegroundColor Cyan

# Create a temporary file with the request
$tempFile = [System.IO.Path]::GetTempFileName()
$request = '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'
Set-Content -Path $tempFile -Value $request

Write-Host "Request: $request" -ForegroundColor Yellow

# Run awswhitelist with input from file
Write-Host ""
Write-Host "Running: type $tempFile | C:\Python312\Scripts\awswhitelist.exe" -ForegroundColor Cyan
$output = type $tempFile | C:\Python312\Scripts\awswhitelist.exe 2>&1

Write-Host ""
Write-Host "Raw output:" -ForegroundColor Yellow
Write-Host $output

# Clean up
Remove-Item $tempFile

# Also try running it directly to see if it starts
Write-Host ""
Write-Host "Testing if awswhitelist starts without input..." -ForegroundColor Cyan
$proc = Start-Process -FilePath "C:\Python312\Scripts\awswhitelist.exe" -NoNewWindow -RedirectStandardError -PassThru
Start-Sleep -Seconds 1

if ($proc.HasExited) {
    Write-Host "Process exited immediately with code: $($proc.ExitCode)" -ForegroundColor Red
    $stderr = $proc.StandardError.ReadToEnd()
    if ($stderr) {
        Write-Host "Error output:" -ForegroundColor Red
        Write-Host $stderr
    }
} else {
    Write-Host "Process is running (good)" -ForegroundColor Green
    $proc.Kill()
}