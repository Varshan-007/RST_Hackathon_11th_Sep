import signal
import sys
import logging
from .neo4j_writer import neo4j_writer
from .kafka_consumer import kafka_consumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("loader")

def handle_signal(sig, frame):
    logger.info(f"Received termination signal {sig}. Shutting down loader...")
    kafka_consumer.stop()
    neo4j_writer.close()
    sys.exit(0)

def main():
    logger.info("Starting Neo4j CSV Loader Service...")
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # 1. Connect to Neo4j with backoff
    if not neo4j_writer.connect():
        logger.error("Failed to connect to Neo4j after maximum retries. Exiting.")
        sys.exit(1)

    # 2. Connect to Kafka with backoff
    if not kafka_consumer.connect():
        logger.error("Failed to connect to Kafka after maximum retries. Exiting.")
        sys.exit(1)

    # 3. Start consuming
    kafka_consumer.start_consuming()

if __name__ == "__main__":
    main()
