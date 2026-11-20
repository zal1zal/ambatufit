#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "Seeding synthetic demo records into AmbatuFit database..."
python scripts/seed_demo.py

