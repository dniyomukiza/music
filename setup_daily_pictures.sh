#!/bin/bash

# Setup script for daily picture generation
# This script sets up a cron job to run the daily picture generation

echo "Setting up daily picture generation..."

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/generate_daily_pictures.py"

# Make the Python script executable
chmod +x "$PYTHON_SCRIPT"

# Create a cron job to run daily at 6 AM
# This will run the script every day at 6:00 AM
(crontab -l 2>/dev/null; echo "0 6 * * * cd $SCRIPT_DIR && python $PYTHON_SCRIPT >> $SCRIPT_DIR/daily_pictures.log 2>&1") | crontab -

echo "✅ Daily picture generation setup complete!"
echo "📅 The script will run daily at 6:00 AM"
echo "🖼️  Will generate 6 pictures per day (3 + 1min pause + 3)"
echo "📝 Logs will be saved to: $SCRIPT_DIR/daily_pictures.log"
echo ""
echo "To view the cron job: crontab -l"
echo "To remove the cron job: crontab -e (then delete the line)"
echo ""
echo "To test the script manually: python $PYTHON_SCRIPT"
