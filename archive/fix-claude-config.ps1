# Fix Claude Desktop config JSON
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

if (Test-Path $configPath) {
    Write-Host "Fixing Claude Desktop config..." -ForegroundColor Green
    
    # Read the file
    $content = Get-Content $configPath -Raw
    
    # Fix the malformed args array (remove whitespace between brackets)
    $content = $content -replace '"args"\s*:\s*\[\s*\]', '"args": []'
    
    # Remove excessive whitespace while preserving structure
    $content = $content -replace ':\s+{', ': {'
    $content = $content -replace ':\s+\[', ': ['
    $content = $content -replace ':\s+"', ': "'
    
    # Save the fixed content
    Set-Content -Path $configPath -Value $content -Encoding UTF8
    
    Write-Host "Config fixed and saved!" -ForegroundColor Green
    
    # Test if it's valid JSON now
    try {
        $test = Get-Content $configPath -Raw | ConvertFrom-Json
        Write-Host "JSON is valid!" -ForegroundColor Green
    } catch {
        Write-Host "JSON still has errors: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Claude Desktop config not found at: $configPath" -ForegroundColor Red
}