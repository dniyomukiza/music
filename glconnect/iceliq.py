# services.py
import os
import json
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
with open('glconfig.json') as json_file:
    config = json.load(json_file)

def start_icecast():
    """Start the Icecast server."""
    icecast_config = config.get('ICECAST_CONFIG')
    if not icecast_config:
        print("ICECAST_CONFIG is not set in the .env file")
        return

    try:
        process = subprocess.Popen(
            ['sudo', '-u', 'icecast', 'icecast', '-c', icecast_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(timeout=5)
        if stderr:
            print(f"Icecast error: {stderr.decode()}")
        else:
            print(f"Icecast server started: {stdout.decode()}")
    except Exception as e:
        print(f"Error starting Icecast server: {e}")

def start_liquidsoap():
    """Start the Liquidsoap script."""
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'liquidconf.liq')
    if not os.path.isfile(script_path):
        print(f"Liquidsoap script not found at {script_path}")
        return

    try:
        process = subprocess.Popen(
            ['liquidsoap', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(timeout=5)
        if stderr:
            print(f"Liquidsoap error: {stderr.decode()}")
        else:
            print("Liquidsoap script started.")
    except Exception as e:
        print(f"Error starting Liquidsoap: {e}")
