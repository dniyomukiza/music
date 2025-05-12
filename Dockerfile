# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /appdir

# Copy only app code and dependencies
COPY . .

# Install dependencies directly in container (no myenv)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the app ports for both Flask and FastAPI
EXPOSE 5000 8001

# Run Flask on port 5000 and FastAPI on port 8001 in background
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:5000 run:app"]




