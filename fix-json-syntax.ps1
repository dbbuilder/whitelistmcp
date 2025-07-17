# Fix JSON syntax errors in Claude Desktop config
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

if (Test-Path $configPath) {
    Write-Host "Fixing JSON syntax errors..." -ForegroundColor Green
    
    # Read the content
    $content = Get-Content $configPath -Raw
    
    # Fix missing comma after closing braces when followed by a quote
    # This regex finds } followed by whitespace and then " without a comma
    $content = $content -replace '(\})\s*(\n\s*")', '$1,$2'
    
    # Fix double closing braces without proper structure
    $content = $content -replace '(\})\s*(\})\s*(\},)', '$1$3'
    
    # Remove any trailing commas before closing braces
    $content = $content -replace ',\s*(\})', '$1'
    
    # Save as UTF-8 without BOM
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($configPath, $content, $utf8NoBom)
    
    Write-Host "JSON syntax fixed!" -ForegroundColor Green
    
    # Try to parse the JSON
    try {
        $test = $content | ConvertFrom-Json
        Write-Host "JSON is now valid!" -ForegroundColor Green
        
        # Pretty print the JSON to verify
        $prettyJson = $test | ConvertTo-Json -Depth 10
        Write-Host ""
        Write-Host "Configuration structure:" -ForegroundColor Cyan
        Write-Host $prettyJson
    } catch {
        Write-Host "JSON still has errors: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please run the create-clean-config.ps1 script to create a fresh configuration." -ForegroundColor Yellow
    }
} else {
    Write-Host "Config file not found at: $configPath" -ForegroundColor Red
}