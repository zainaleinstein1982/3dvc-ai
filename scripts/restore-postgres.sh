#!/bin/bash
CONTAINER_NAME="3dvc-postgres"
DB_USER="threedvc"
DB_NAME="threedvc_db"
FILE=$1

if [ -z "$FILE" ]; then
  echo "Please provide backup file path."
  exit 1
fi

echo "Restoring $FILE to $DB_NAME..."
gunzip -c $FILE | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME
echo "Restore complete."
