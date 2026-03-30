# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy the rest of the application code
COPY src /app/src

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the API port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "velocity.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
