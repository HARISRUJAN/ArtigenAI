#!/bin/bash
# Azure App Service startup script
# Azure sets the PORT environment variable, default to 8000 if not set

PORT=${PORT:-8000}
echo "Starting application on port $PORT"

python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
