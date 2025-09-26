#!/bin/bash
export PYTHONPATH=/app
# Start the ingester for real GTFS data in background
python -m app.ingester &

# Start the FastAPI server in foreground
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
