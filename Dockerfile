# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory
WORKDIR /appdir

# Copy the application code into the container
COPY . .

# Copy the virtual environment into the container (myenv should be in the same directory as your Dockerfile)
COPY myenv /appdir/myenv

# Set the environment to use the virtualenv
ENV PATH="/appdir/myenv/bin:$PATH"

# Install any required dependencies (if not already included in myenv)
RUN pip install -r requirements.txt

# Expose the port if the app serves HTTP requests (e.g., Flask app)
EXPOSE 5000

# Command to run the app (using gunicorn to serve)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]
