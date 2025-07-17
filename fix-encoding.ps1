# Fix Claude Desktop config file encoding
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

if (Test-Path $configPath) {
    Write-Host "Checking file encoding..." -ForegroundColor Green
    
    # Read the file as bytes to check for BOM
    $bytes = [System.IO.File]::ReadAllBytes($configPath)
    
    # Check for UTF-8 BOM (EF BB BF)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host "File has UTF-8 BOM, removing..." -ForegroundColor Yellow
        
        # Read content and save without BOM
        $content = Get-Content $configPath -Raw -Encoding UTF8
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($configPath, $content, $utf8NoBom)
        
        Write-Host "BOM removed!" -ForegroundColor Green
    }
    
    # Read the content
    $content = Get-Content $configPath -Raw
    
    # Check for common encoding issues - remove control characters
    if ($content -match '[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]') {
        Write-Host "Found control characters, cleaning..." -ForegroundColor Yellow
        $content = $content -replace '[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ''
    }
    
    # Save as UTF-8 without BOM
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($configPath, $content, $utf8NoBom)
    
    Write-Host "File encoding fixed!" -ForegroundColor Green
    
    # Try to parse the JSON
    try {
        $test = $content | ConvertFrom-Json
        Write-Host "JSON is valid!" -ForegroundColor Green
    } catch {
        Write-Host "JSON parsing error: $_" -ForegroundColor Red
        Write-Host "First 200 characters of file:" -ForegroundColor Yellow
        Write-Host $content.Substring(0, [Math]::Min(200, $content.Length))
    }
} else {
    Write-Host "Config file not found at: $configPath" -ForegroundColor Red
}