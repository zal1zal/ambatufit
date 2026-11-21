#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

echo "Creating AmbatuFit STB database backup..."
if [ -f "./var/ambatufit.db" ]; then
    cp "./var/ambatufit.db" "$BACKUP_DIR/ambatufit_backup_$TIMESTAMP.db"
    echo "Backup created at $BACKUP_DIR/ambatufit_backup_$TIMESTAMP.db"
else
    echo "Copying from Docker container ambatufit-core-service-1:/data/ambatufit.db..."
    docker compose cp core-service:/data/ambatufit.db "$BACKUP_DIR/ambatufit_backup_$TIMESTAMP.db" || true
    echo "Docker backup completed."
fi

