# Root Dockerfile for Railway deployment (Backend)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and code
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code
COPY backend/ .

# Expose port (Railway will use PORT environment variable)
EXPOSE 8000

# Run the FastAPI server
CMD ["python", "main.py"]
