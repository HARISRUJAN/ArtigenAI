# Multi-stage build for AI Governance Platform
# Stage 1: Frontend build
# Note: This Dockerfile should be built from the repository root directory
# Build command: docker build -f backend/Dockerfile -t aigov-app .
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm ci --only=production=false

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python dependencies builder
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser backend/ .

# Copy frontend static files from frontend builder
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist /app/static

# Add local bin to PATH for user
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
# Use Python's built-in urllib instead of requests (which may not be installed)
# Note: Health check uses port 8000 (default), Azure will map this to the PORT env var
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run the application
# Use PORT environment variable (Azure sets this) or default to 8000
# Note: Azure Web App sets PORT env var, so we use shell form to interpolate it
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4

