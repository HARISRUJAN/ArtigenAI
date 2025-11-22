#!/bin/bash
# Azure App Service startup script for ArtigenAI

# Change to backend directory where the app code is
cd backend

# Install spaCy language model if not already installed (in background to not delay startup)
# This is needed for semantic chunking functionality
(python -m spacy download en_core_web_md --quiet 2>/dev/null || echo "spaCy model installation skipped") &

# Start the FastAPI application with Gunicorn
# Use Gunicorn for production as it's more robust than uvicorn alone
# Azure App Service sets the PORT environment variable
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
