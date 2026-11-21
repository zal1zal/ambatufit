$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
Write-Host "Starting AmbatuFit Integration Service (Off-STB) on port 8200..." -ForegroundColor Cyan
python -m uvicorn integration.server:app --reload --host 0.0.0.0 --port 8200

