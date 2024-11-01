# Use Ubuntu as the base image
FROM ubuntu:latest

# Install Python and other dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create and set permissions on the log file
RUN touch /var/log/cron.log && chmod 0666 /var/log/cron.log

# Set the entrypoint to the script, which will run the Python script every 3 minutes
CMD ["/app/entrypoint.sh"]
