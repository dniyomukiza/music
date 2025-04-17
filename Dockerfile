# Step 1: Base Image for Flask App
FROM python:3.10-slim AS app-base

WORKDIR /appdir

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000
EXPOSE 8001

# Step 2: Icecast Setup
FROM deepcomp/icecast2 AS icecast-base

COPY ./icecast.xml /etc/icecast.xml

EXPOSE 8000

# Step 3: Liquidsoap Setup
FROM phasecorex/liquidsoap:latest AS liquidsoap-base

COPY ./scripts /liqfolder/scripts

# Step 4: Final Image - Combine Everything
FROM python:3.10-slim

# Create workdir
WORKDIR /appdir

# Copy Flask app
COPY --from=app-base /appdir /appdir

# Copy Icecast config
COPY --from=icecast-base /etc/icecast.xml /etc/icecast.xml

# Copy Liquidsoap scripts
COPY --from=liquidsoap-base /liqfolder/scripts /liqfolder/scripts

# Install Flask and deps
RUN pip install -r /appdir/requirements.txt

# Copy start_all.sh script
COPY start_all.sh /appdir/start_all.sh
RUN chmod +x /appdir/start_all.sh

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

EXPOSE 5000
EXPOSE 8000
EXPOSE 8001

# Run all services via script
CMD ["/appdir/start_all.sh"]
