# Step 1: Base Image for Flask App
FROM python:3.10-slim AS app-base

# Set the working directory for the Flask app
WORKDIR /appdir

# Copy the application code into the container
COPY . .

# Install Flask and other required dependencies
RUN pip install -r requirements.txt

# Expose ports for Flask and other services
EXPOSE 5000
EXPOSE 8001

# Step 2: Icecast Setup
FROM deepcomp/icecast2 AS icecast-base

# Copy your icecast configuration (if any)
COPY ./icecast.xml /etc/icecast.xml

# Expose Icecast port
EXPOSE 8000

# Step 3: Liquidsoap Setup
FROM phasecorex/liquidsoap:latest AS liquidsoap-base

# Copy the Liquidsoap scripts
COPY ./scripts /liqfolder/scripts

# Step 4: Final Image - Combine Everything
FROM python:3.10-slim

# Copy over the Flask app build from the previous stage
COPY --from=app-base /appdir /appdir

# Copy Icecast files
COPY --from=icecast-base /etc/icecast.xml /etc/icecast.xml

# Copy Liquidsoap scripts
COPY --from=liquidsoap-base /liqfolder/scripts /liqfolder/scripts

# Install any dependencies for Flask
RUN pip install -r /appdir/requirements.txt

# Set environment variables (for Flask)
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Expose the necessary ports
EXPOSE 5000
EXPOSE 8000
EXPOSE 8001

# Start all services together
CMD ["sh", "-c", "python /appdir/run.py & uvicorn /appdir/glconnect.voc:app --reload --host 0.0.0.0 --port 8001 & /usr/bin/icecast -c /etc/icecast.xml -b & liquidsoap /liqfolder/scripts/main.liq"]
