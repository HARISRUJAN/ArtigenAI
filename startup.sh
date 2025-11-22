#!/bin/bash
# Azure App Service startup script for ArtigenAI

# Change to backend directory where the app code is
cd backend

# Check if spaCy model is already installed, if not, install it
# This is needed for semantic chunking functionality
# Note: First startup may be slower while model downloads
if ! python -c "import spacy; spacy.load('en_core_web_md')" 2>/dev/null; then
    echo "INFO: Installing spaCy language model (en_core_web_md)..."
    echo "INFO: This is a one-time operation and may take 1-2 minutes..."
    python -m spacy download en_core_web_md || {
        echo "WARNING: spaCy model installation failed. Semantic chunking may not work correctly."
        echo "INFO: You can install it manually via Azure SSH: python -m spacy download en_core_web_md"
    }
fi

# Start the FastAPI application with Gunicorn
# Use Gunicorn for production as it's more robust than uvicorn alone
# Azure App Service sets the PORT environment variable
# WORKERS environment variable can be set in Azure Portal (default: 4)
echo "INFO: Starting Gunicorn with ${WORKERS:-4} workers on port ${PORT:-8000}..."
gunicorn app.main:app \
    --workers ${WORKERS:-4} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
