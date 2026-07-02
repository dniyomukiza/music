#!/bin/bash
# Run the accountability columns migration
# This script connects to your PostgreSQL database and runs the migration

DB_URL="${DATABASE_URL:-${DB_URL:-}}"
if [ -z "$DB_URL" ]; then
    echo "❌ Set DATABASE_URL or DB_URL before running this migration."
    exit 1
fi

echo "Running migration: add_accountability_columns.sql"
echo "Connecting to database..."

# Run the migration
psql "$DB_URL" -f add_accountability_columns.sql

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
else
    echo "❌ Migration failed. Please check the error above."
    exit 1
fi


