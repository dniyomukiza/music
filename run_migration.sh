#!/bin/bash
# Run the accountability columns migration
# This script connects to your PostgreSQL database and runs the migration

# Database connection details
if [ -z "$DATABASE_URL" ] && [ -z "$DB_URL" ]; then
    echo "Error: DATABASE_URL or DB_URL environment variable is not set." >&2
    exit 1
fi

DB_URL="${DATABASE_URL:-$DB_URL}"

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


