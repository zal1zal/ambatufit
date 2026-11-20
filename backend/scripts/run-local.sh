#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "Starting AmbatuFit STB Core API locally on port 8000..."
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

