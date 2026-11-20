$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
Write-Host "Starting AmbatuFit STB Core API locally on port 8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

