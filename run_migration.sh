#!/bin/bash
# Run the accountability columns migration
# This script connects to your PostgreSQL database and runs the migration

# Database connection details (from docker-compose.yml)
DB_URL="postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr"

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


