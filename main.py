import json
from loguru import logger
from sqlalchemy import create_engine, Column, String, Boolean, Integer, DateTime, Text, JSON, text  # Added JSON type
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import NoResultFound, MultipleResultsFound, IntegrityError
from dotenv import load_dotenv
from uuid import uuid5, NAMESPACE_DNS
from datetime import datetime, timezone
import os
import feedparser
from confluent_kafka import Producer

# Load environment variables
load_dotenv()

# PostgreSQL database connection details from environment
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
SOURCEID = os.getenv("SOURCEID")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")

# Set up the database URI and SQLAlchemy engine
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL, echo=os.getenv("POSTGRES_ECHO", "false").lower() == "true",
                       pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "5")))
SessionLocal = sessionmaker(bind=engine)

# Define SQLAlchemy models
Base = declarative_base()

class Source(Base):
    __tablename__ = 'sources'

    sourceid = Column(String, primary_key=True)
    enabled = Column(Boolean, nullable=False)
    sourcetype = Column(String, nullable=False)
    sourcename = Column(String, nullable=False)
    sourcelocation = Column(String, nullable=False)
    lastinterrogation = Column(DateTime, default=datetime.now(timezone.utc))
    created = Column(DateTime, default=datetime.now(timezone.utc))
    updated = Column(DateTime, default=datetime.now(timezone.utc))
    numprocessed = Column(Integer, default=0)
    articleelement = Column(JSON)  # New JSON column for articleelement

class CollectedArtefact(Base):
    __tablename__ = 'collected_artefacts'

    artefactid = Column(String, primary_key=True)
    description = Column(Text, nullable=False)
    sourceid = Column(String, nullable=False)  # Foreign key reference to Source
    locator = Column(Text, nullable=False)  # Stores the RSS entry link
    created = Column(DateTime, default=datetime.now(timezone.utc))

# Setup Kafka Producer
kafka_producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

# Log configuration
logger.add("application.log", rotation="500 MB")

# Function to connect to the database and retrieve the source entry
def get_source_by_id(session, source_id):
    try:
        source = session.query(Source).filter(Source.sourceid == source_id).one()
        return source
    except NoResultFound:
        logger.error("No source found with sourceid: {}", source_id)
        exit(1)
    except MultipleResultsFound:
        logger.error("Multiple sources found with sourceid: {}", source_id)
        exit(1)

# Function to create a unique UUID based on RSS feed entry details
def create_unique_uid(title, link, description, pubDate):
    unique_str = f"{title}-{link}-{description}-{pubDate}"
    return str(uuid5(NAMESPACE_DNS, unique_str))

# Function to post to Kafka topic with JSON message
def post_to_kafka(topic, key, message):
    kafka_producer.produce(topic, key=key, value=json.dumps(message))
    kafka_producer.flush()

# Main application logic
def main():
    with SessionLocal() as session:
        # Get source information by SOURCEID
        source = get_source_by_id(session, SOURCEID)

        # Check if the source is enabled
        if not source.enabled:
            logger.info("Source with sourceid {} is disabled. Exiting.", SOURCEID)
            exit(0)

        # Parse RSS feed from sourcelocation
        feed = feedparser.parse(source.sourcelocation)
        if not feed.entries:
            logger.warning("No entries found in the RSS feed at {}", source.sourcelocation)
            return

        # Insert RSS feed entries into collected_artefacts and track duplicates
        num_entries = 0
        duplicates = []
        for entry in feed.entries:
            uid = create_unique_uid(entry.title, entry.link, entry.description, entry.published)
            artefact_description = f"{source.sourcetype} from {source.sourcename} - {entry.title}"

            artefact = CollectedArtefact(
                artefactid=uid,
                description=artefact_description,
                sourceid=source.sourceid,
                locator=entry.link
            )

            try:
                session.add(artefact)
                session.commit()
                num_entries += 1

                # Prepare and send a Kafka message for the collected_artefact entry
                artefact_message = {
                    "artefactid": uid,
                    "sourcetype": source.sourcetype,
                    "description": artefact_description,
                    "sourceid": source.sourceid,
                    "locator": entry.link,
                    "created": datetime.now(timezone.utc).isoformat(),
                    "articleelement": source.articleelement  # Adding the new articleelement field
                }
                post_to_kafka("collected_artefacts", uid, artefact_message)
                logger.info("Kafka message sent to 'collected_artefacts' with key '{}': {}", uid, artefact_message)

            except IntegrityError:
                session.rollback()
                logger.warning(
                    "Duplicate entry detected with artefactid {}. Description: '{}', SourceID: '{}', Locator: '{}'",
                    uid, artefact_description, source.sourceid, entry.link
                )
                duplicates.append({
                    "artefactid": uid,
                    "description": artefact_description,
                    "sourceid": source.sourceid,
                    "locator": entry.link
                })
            except Exception as e:
                logger.error("Unexpected error occurred: {}", str(e))
                session.rollback()

        # Update numprocessed and lastinterrogation in sources table
        source.numprocessed = num_entries
        source.lastinterrogation = datetime.now(timezone.utc)
        session.commit()

        # Prepare Kafka message with all source attributes and duplicates list if any
        kafka_key = f"{SOURCEID}_{datetime.now(timezone.utc).date()}"
        kafka_message = {
            "sourceid": source.sourceid,
            "enabled": source.enabled,
            "sourcetype": source.sourcetype,
            "sourcename": source.sourcename,
            "sourcelocation": source.sourcelocation,
            "articleelement": source.articleelement,
            "lastinterrogation": source.lastinterrogation.isoformat() if source.lastinterrogation else None,
            "created": source.created.isoformat() if source.created else None,
            "updated": source.updated.isoformat() if source.updated else None,
            "numprocessed": source.numprocessed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duplicates": duplicates
        }

        # Post JSON message to Kafka with key
        post_to_kafka("sources", kafka_key, kafka_message)
        logger.info("Kafka message sent to 'sources' with key '{}': {}", kafka_key, kafka_message)

    logger.info("Application run complete.")

if __name__ == "__main__":
    main()
