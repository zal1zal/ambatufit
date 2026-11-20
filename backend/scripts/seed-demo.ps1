$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
Write-Host "Seeding synthetic demo records into AmbatuFit database..." -ForegroundColor Cyan
python scripts/seed_demo.py

