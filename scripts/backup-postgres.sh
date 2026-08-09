#!/bin/bash
CONTAINER_NAME="3dvc-postgres"
DB_USER="threedvc"
DB_NAME="threedvc_db"
BACKUP_DIR="./backups"

mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

echo "Backing up $DB_NAME to $FILE..."
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > $FILE
echo "Backup complete."
