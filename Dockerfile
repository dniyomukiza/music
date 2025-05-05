# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /appdir

# Copy the application code into the container
COPY . .

# Install any required dependencies
RUN pip install -r requirements.txt

# Expose the port if the app serves HTTP requests (e.g., Flask app)
EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]


