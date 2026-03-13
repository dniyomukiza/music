#!/bin/bash
# Run the book platform voice agent
# Requires: .env with DB_URL, GOOGLE_API_KEY (or GEMINI_API_KEY)

set -e
cd "$(dirname "$0")"

# Activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
elif [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# .env is loaded by the app via python-dotenv (avoids source .env breaking on complex values)

# Run uvicorn (app.main:app when run from voice_agent/)
uvicorn app.main:app --host 0.0.0.0 --port 8001
