#!/bin/sh

# Start all services in the background
python /appdir/run.py &
uvicorn /appdir/glconnect.voc:app --reload --host 0.0.0.0 --port 8001 &
/usr/bin/icecast -c /etc/icecast.xml -b &
liquidsoap /liqfolder/scripts/main.liq
