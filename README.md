
# Python Dockerized Application

This project runs a Python application in a Docker container that executes every hour using `cron`.

## Requirements

- Docker
- Docker Compose

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/project-folder.git
   cd project-folder
   ```

2. **Set up environment variables:**
   - Copy the `.env.example` file to `.env` and fill in your values.
   
   ```bash
   cp .env.example .env
   ```

3. **Build and run the application:**

   ```bash
   docker-compose up --build -d
   ```

4. **Verify the application is running:**
   - Check the logs to confirm the cron job is running:

   ```bash
   docker logs -f maggie
   ```

## Stopping the Application

To stop the application, run:

```bash
docker-compose down
```

## Notes

- Logs are written to `/var/log/cron.log` inside the container.
