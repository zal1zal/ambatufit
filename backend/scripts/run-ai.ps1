$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
Write-Host "Starting AmbatuFit AI Inference Service (Off-STB) on port 8100..." -ForegroundColor Cyan
python -m uvicorn ai.server:app --reload --host 0.0.0.0 --port 8100

