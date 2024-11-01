#!/bin/bash
while true
do
    echo "Running script at $(date)"
    python3 /app/main.py >> /var/log/cron.log 2>&1
    sleep 3600  # Wait 3 minutes before running again
done
