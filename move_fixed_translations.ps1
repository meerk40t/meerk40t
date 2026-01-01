# Move fixed translation files to their locale directories
# Pattern: fixed_XX_meerk40t.po -> locale\XX\LC_MESSAGES\meerk40t.po

$fixedFiles = Get-ChildItem -Path "." -Filter "fixed_*_meerk40t.po"

if ($fixedFiles.Count -eq 0) {
    Write-Host "No fixed_*_meerk40t.po files found in current directory." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($fixedFiles.Count) fixed translation file(s):" -ForegroundColor Cyan
$fixedFiles | ForEach-Object { Write-Host "  - $($_.Name)" }
Write-Host ""

foreach ($file in $fixedFiles) {
    # Extract language code from filename: fixed_XX_meerk40t.po or fixed_XX_YY_meerk40t.po
    if ($file.Name -match '^fixed_(.+?)_meerk40t\.po$') {
        $langCode = $Matches[1]
        
        $targetDir = ".\locale\$langCode\LC_MESSAGES"
        $targetFile = "$targetDir\meerk40t.po"
        
        # Check if target directory exists
        if (-not (Test-Path $targetDir)) {
            Write-Host "Creating directory: $targetDir" -ForegroundColor Yellow
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        
        # Move and overwrite
        Write-Host "Moving: $($file.Name) -> $targetFile" -ForegroundColor Green
        Move-Item -Path $file.FullName -Destination $targetFile -Force
        
        Write-Host "  Successfully moved" -ForegroundColor Green
    }
    else {
        Write-Host "Skipping $($file.Name) - does not match expected pattern" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "All translation files moved successfully!" -ForegroundColor Green
