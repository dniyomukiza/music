# Project Setup Guide

## Table of Contents

- [Project Setup Guide](#project-setup-guide)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Build Docker Image](#build-docker-image)
  - [Run with Docker Compose](#run-with-docker-compose)
  - [Run Flask App Locally](#run-flask-app-locally)

## Installation

Follow the steps below to set up the project locally:

1. **Clone the repository**:
    ```bash
    git clone https://github.com/dniyomukiza/music.git
    ```

2. **Install Python environment**:
    Create a virtual environment for the project:
    ```bash
    python3 -m venv venv
    ```

3. **Activate the environment**:
    - **macOS/Linux**:
        ```bash
        source venv/bin/activate
        ```
    - **Windows**:
        ```bash
        .\venv\Scripts\activate
        ```

4. **Install dependencies**:
    Install all the required packages listed in `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

5. **Set up environment variables**:
    Ensure you have the necessary environment variables configured in a `.env` file.

---

## Build Docker Image

Since the Docker image is not yet shared, you will need to build it locally:

1. **Build the Docker image**:
    ```bash
    docker build -t myapp:latest .
    ```

2. **Stop any running containers** (if needed):
    ```bash
    docker-compose down
    ```

3. **Rebuild and start the Docker containers**:
    ```bash
    docker-compose up --build
    ```

**Note**: Be sure to have Docker Engine installed and running on your machine.

---

## Run with Docker Compose

To run the application using Docker Compose, follow these steps:

1. **Start the application with Docker Compose**:
    ```bash
    docker-compose up
    ```

2. **Stop the application**:
    ```bash
    docker-compose down
    ```

---

## Run Flask App Locally

To run the Flask app locally in debug mode:

1. **Set Flask environment variables**:
    - **macOS/Linux**:
        ```bash
        export FLASK_APP=run.py
        export FLASK_DEBUG=1
        ```
    - **Windows**:
        ```bash
        set FLASK_APP=run.py
        set FLASK_DEBUG=1
        ```

2. **Start the Flask app**:
    ```bash
    flask run
    ```

The Flask application should now be running locally at `http://127.0.0.1:5000`