# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /usr/src/appdir

# Set environment variables for memory optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MALLOC_ARENA_MAX=2
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_MMAP_MAX_=65536

# Install system dependencies: ffmpeg for audio, node for yt-dlp JS runtime (YouTube)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with memory optimization
RUN pip install --no-cache-dir --verbose -r requirements.txt

# Verify FFmpeg installation (ffprobe is included with ffmpeg)
RUN ffmpeg -version && ffprobe -version

# Copy the rest of the application code
COPY . .

# Create a non-root user for security and memory efficiency
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /usr/src/appdir
USER appuser

# Expose the app ports for both Flask and FastAPI
EXPOSE 5000 8001

# Run Flask on port 5000 and FastAPI on port 8001 in background
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:5000 run:app"]




