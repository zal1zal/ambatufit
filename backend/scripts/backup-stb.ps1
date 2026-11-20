$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = ".\backups"
if (!(Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }

Write-Host "Creating AmbatuFit STB database backup..." -ForegroundColor Cyan
if (Test-Path ".\var\ambatufit.db") {
    Copy-Item ".\var\ambatufit.db" "$BackupDir\ambatufit_backup_$Timestamp.db"
    Write-Host "Backup created at $BackupDir\ambatufit_backup_$Timestamp.db" -ForegroundColor Green
} else {
    Write-Host "Local db file not found. Trying Docker Compose cp..."
    docker compose cp core-service:/data/ambatufit.db "$BackupDir\ambatufit_backup_$Timestamp.db"
}

