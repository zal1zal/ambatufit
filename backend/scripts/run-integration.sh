#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "Starting AmbatuFit Integration Service (Off-STB) on port 8200..."
python -m uvicorn integration.server:app --reload --host 0.0.0.0 --port 8200

