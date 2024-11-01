
# Maggie - RSS Feed Processor

## Run Requirements

- The .env file must have a SOURCEID which is a primary key of the sources table
- The tables must exist in the PostgressDB
```postgresql
CREATE TABLE IF NOT EXISTS sources (
 sourceid VARCHAR PRIMARY KEY,
 enabled BOOLEAN NOT NULL,
 sourcetype VARCHAR NOT NULL,
 sourcename VARCHAR NOT NULL,
 sourcelocation VARCHAR NOT NULL,
 lastinterrogation TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
 created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
 updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
 numprocessed INTEGER DEFAULT 0,
 articleelement JSON  -- New JSON column for storing HTML element details
 );


CREATE TABLE IF NOT EXISTS collected_artefacts (
    artefactid UUID PRIMARY KEY,
    description TEXT NOT NULL,
    sourceid VARCHAR REFERENCES sources(sourceid) ON DELETE CASCADE,
    locator TEXT NOT NULL,
    rawcontent TEXT, -- Use TEXT for large amounts of text data, such as blog HTML content
    created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```
- And have at least one entry in the sources table
```postgresql
   INSERT INTO sources (
    sourceid,
    enabled,
    sourcetype,
    sourcename,
    sourcelocation,
    lastinterrogation,
    created,
    updated,
    numprocessed,
    articleelement
) VALUES (
    '018f8748-1b51-750e-9971-19e75ea1db13', -- sourceid (UUID format string)
    TRUE,                                   -- enabled (boolean)
    'RSS',                                  -- sourcetype (limited to defined values)
    'www.globenewswire.com - Corporate Action',                       -- sourcename (source name)
    'https://www.globenewswire.com/RssFeed/subjectcode/61-Corporate%20Action/feedTitle/GlobeNewswire%20-%20Corporate%20Action',              -- sourcelocation (URL of the RSS feed)
    '2024-10-31 10:00:00+00',               -- lastinterrogation (timestamp with timezone)
    '2024-10-01 08:30:00+00',               -- createdat (timestamp with timezone)
    '2024-10-30 15:45:00+00',               -- updated (timestamp with timezone)
    0,                                      -- numprocessed (integer)
	'{"div": ["col-sm-10 col-sm-offset-1", "col-lg-10 col-lg-offset-1"]}'  -- articleelement (JSON data)
);
```

## Deployment Requirements

- Docker
- Docker Compose

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/dannykellett/maggie.git
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

## Architecture flow

- entrypoint.sh loop timer
- reads sourceid from .env and makes a query to the sources table in the db
- uses url from sources row to call out to rss feed
- saves to collected_artefacts table in postgress
- creates an entry in collected_artefacts_rss_pre_scrape kafka topic

## Notes

- Logs are written to `/application.log` inside the container.
