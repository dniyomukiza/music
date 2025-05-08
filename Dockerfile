# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /appdir

# Copy only app code and dependencies
COPY . .

# Install dependencies directly in container (no myenv)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the app port
EXPOSE 5000

# Run with gunicorn
CMD ["sh", "-c", "gunicorn glconnect.voc:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 & uvicorn glconnect.voc:app --host 0.0.0.0 --port 5000"]




