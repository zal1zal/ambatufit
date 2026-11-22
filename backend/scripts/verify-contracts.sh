#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python -m pytest tests/test_api_contracts.py -q

