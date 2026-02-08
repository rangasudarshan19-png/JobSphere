# PowerShell Script to Create Desktop Shortcut for Job Tracker

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Creating Desktop Shortcut" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get paths
$StartupScriptPath = "$PSScriptRoot\START_ALL.bat"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$DesktopPath\🚀 Job Tracker.lnk"

# Check if startup script exists
if (-not (Test-Path $StartupScriptPath)) {
    Write-Host "❌ Error: START_ALL.bat not found!" -ForegroundColor Red
    Write-Host "   Expected location: $StartupScriptPath" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✓ Found startup script: START_ALL.bat" -ForegroundColor Green
Write-Host ""

# Create shortcut
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $StartupScriptPath
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.Description = "Start Job Tracker (Backend + Frontend + Gemini AI)"
    $Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,137"  # Rocket/Star icon
    $Shortcut.Save()
    
    Write-Host "✅ Desktop shortcut created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📍 Shortcut location: $ShortcutPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🚀 You can now:" -ForegroundColor Yellow
    Write-Host "   1. Double-click the '🚀 Job Tracker' icon on your desktop" -ForegroundColor White
    Write-Host "   2. Everything will start automatically!" -ForegroundColor White
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Failed to create shortcut: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
pause
