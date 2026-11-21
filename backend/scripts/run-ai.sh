#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "Starting AmbatuFit AI Inference Service (Off-STB) on port 8100..."
python -m uvicorn ai.server:app --reload --host 0.0.0.0 --port 8100

