#!/bin/bash
while true
do
    echo "Running script at $(date)"
    python3 /app/main.py 2>&1
    sleep 10800  # Wait an 3 hours before running again
done
