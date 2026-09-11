import json
import logging
import time
from typing import Optional
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable, KafkaError
from .config import settings
from .neo4j_writer import neo4j_writer

logger = logging.getLogger("loader.consumer")

class KafkaLoaderConsumer:
    def __init__(self):
        self._consumer: Optional[KafkaConsumer] = None
        self._running = False

    def connect(self, max_retries: int = 30, retry_delay: float = 2.0) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Connecting Kafka consumer to {settings.kafka_bootstrap_servers} (Attempt {attempt}/{max_retries})...")
                self._consumer = KafkaConsumer(
                    settings.kafka_topic,
                    bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                    group_id=settings.kafka_group_id,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    consumer_timeout_ms=1000
                )
                logger.info(f"Subscribed to Kafka topic: {settings.kafka_topic}")
                return True
            except (NoBrokersAvailable, KafkaError) as e:
                logger.warning(f"Kafka broker not ready: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Unexpected error connecting to Kafka: {e}")
                time.sleep(retry_delay)
        return False

    def start_consuming(self):
        self._running = True
        logger.info("Starting message consumption loop...")

        while self._running:
            try:
                if self._consumer is None:
                    if not self.connect():
                        time.sleep(2.0)
                        continue

                # Poll messages with short timeout
                msg_pack = self._consumer.poll(timeout_ms=500, max_records=50)
                if not msg_pack:
                    continue

                for tp, messages in msg_pack.items():
                    for message in messages:
                        try:
                            val = message.value
                            neo4j_writer.merge_row(val)
                        except Exception as e:
                            logger.error(f"Error processing Kafka message at offset {message.offset}: {e}")
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                time.sleep(1.0)

    def stop(self):
        logger.info("Stopping Kafka consumer...")
        self._running = False
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass
            self._consumer = None

kafka_consumer = KafkaLoaderConsumer()
