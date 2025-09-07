# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /appdir

# Install system dependencies first (for better caching)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Add verbose output and no cache to see progress
RUN pip install --no-cache-dir --verbose -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the app ports for both Flask and FastAPI
EXPOSE 5000 8001

# Run Flask on port 5000 and FastAPI on port 8001 in background
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:5000 run:app"]




