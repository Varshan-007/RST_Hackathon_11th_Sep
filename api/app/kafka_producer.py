import json
import logging
import time
from typing import List, Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable, KafkaError
from .config import settings

logger = logging.getLogger("api.kafka")

class KafkaProducerClient:
    def __init__(self):
        self._producer: Optional[KafkaProducer] = None

    def connect(self, retries: int = 3, delay: float = 1.0) -> bool:
        for attempt in range(retries):
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",
                    retries=3,
                    request_timeout_ms=5000,
                    max_block_ms=5000
                )
                logger.info("Connected to Kafka producer successfully.")
                return True
            except NoBrokersAvailable:
                logger.warning(f"Kafka brokers unavailable, attempt {attempt + 1}/{retries}")
                time.sleep(delay)
            except Exception as e:
                logger.warning(f"Failed to create Kafka producer: {e}")
                time.sleep(delay)
        return False

    def is_connected(self) -> bool:
        if self._producer is None:
            return self.connect(retries=1)
        try:
            # Check bootstrap connectivity
            return bool(self._producer.bootstrap_connected())
        except Exception:
            return False

    def send_row(self, topic: str, message: Dict[str, Any]):
        if not self.is_connected():
            if not self.connect(retries=2):
                raise ConnectionError("Kafka broker is not reachable")
        try:
            self._producer.send(topic, message)
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
            raise e

    def send_batch(self, topic: str, messages: List[Dict[str, Any]]):
        if not self.is_connected():
            if not self.connect(retries=2):
                raise ConnectionError("Kafka broker is not reachable")
        try:
            for msg in messages:
                self._producer.send(topic, msg)
            self._producer.flush(timeout=5.0)
        except Exception as e:
            logger.error(f"Error sending batch to Kafka: {e}")
            raise e

    def flush(self):
        if self._producer:
            self._producer.flush()

    def close(self):
        if self._producer:
            self._producer.close()
            self._producer = None

kafka_producer = KafkaProducerClient()
