# Multi-stage build for Railway deployment
# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN npm run build

# Stage 2: Backend with Frontend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (includes chroma_db if it exists)
COPY backend/ .

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# If chroma_db exists locally, it will be copied above
# The app will use web search fallback if ChromaDB is empty
# Or set RUN_INGESTION=true in Railway to populate at startup

# Make startup script executable
RUN chmod +x /app/startup.sh

# Expose port (Railway will use PORT environment variable)
EXPOSE 8080

# Run startup script (checks for ChromaDB, runs ingestion if needed, then starts server)
CMD ["/bin/bash", "/app/startup.sh"]
