import logging
import time
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase, Driver
from .config import settings

logger = logging.getLogger("loader.neo4j")

class Neo4jWriter:
    def __init__(self):
        self._driver: Optional[Driver] = None

    def connect(self, max_retries: int = 30, retry_delay: float = 2.0) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Connecting to Neo4j at {settings.neo4j_uri} (Attempt {attempt}/{max_retries})...")
                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                    max_connection_lifetime=200,
                    max_connection_pool_size=50
                )
                self._driver.verify_connectivity()
                logger.info("Connected to Neo4j successfully!")
                self._create_indexes()
                return True
            except Exception as e:
                logger.warning(f"Neo4j not ready yet: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
        return False

    def _create_indexes(self):
        """Create constraints / indexes for high performance idempotent MERGEs."""
        queries = [
            "CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
            "CREATE INDEX row_dataset_idx IF NOT EXISTS FOR (r:Row) ON (r.dataset_id, r.row_index)",
            "CREATE CONSTRAINT job_id_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.id IS UNIQUE"
        ]
        with self._driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    logger.warning(f"Index creation note: {e}")

    def is_connected(self) -> bool:
        if self._driver is None:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def merge_row(self, msg: Dict[str, Any]) -> bool:
        """
        Idempotently writes a single CSV row to Neo4j and updates Job status.
        Returns True on success, False on error.
        """
        job_id = msg.get("job_id")
        dataset_id = msg.get("dataset_id")
        filename = msg.get("filename", "unknown.csv")
        row_index = int(msg.get("row_index", 0))
        rows_total = int(msg.get("rows_total", 1))
        data = msg.get("data", {})

        # Prepare properties
        row_props = dict(data)
        row_props["dataset_id"] = dataset_id
        row_props["row_index"] = row_index

        cypher = """
        MERGE (d:Dataset {id: $dataset_id})
          ON CREATE SET d.filename = $filename, d.uploaded_at = datetime(), d.row_count = $rows_total
        MERGE (r:Row {dataset_id: $dataset_id, row_index: $row_index})
          ON CREATE SET r += $props
          ON MATCH SET r += $props
        MERGE (d)-[:HAS_ROW]->(r)
        WITH d, r
        MERGE (j:Job {id: $job_id})
          ON CREATE SET j.dataset_id = $dataset_id,
                        j.status = 'loading',
                        j.rows_total = $rows_total,
                        j.rows_loaded = 1,
                        j.rows_failed = 0,
                        j.created_at = datetime(),
                        j.updated_at = datetime()
          ON MATCH SET j.rows_loaded = j.rows_loaded + 1,
                       j.status = CASE WHEN (j.rows_loaded + 1 + j.rows_failed) >= j.rows_total THEN 'complete' ELSE 'loading' END,
                       j.updated_at = datetime()
        """
        try:
            with self._driver.session() as session:
                session.run(cypher, {
                    "dataset_id": dataset_id,
                    "filename": filename,
                    "row_index": row_index,
                    "rows_total": rows_total,
                    "props": row_props,
                    "job_id": job_id
                })
            return True
        except Exception as e:
            logger.error(f"Failed to MERGE row {row_index} for dataset {dataset_id}: {e}")
            self.record_failure(job_id=job_id, dataset_id=dataset_id, rows_total=rows_total)
            return False

    def merge_batch(self, messages: List[Dict[str, Any]]):
        """Processes a batch of messages in a single transaction for maximum throughput."""
        if not messages:
            return

        for msg in messages:
            self.merge_row(msg)

    def record_failure(self, job_id: str, dataset_id: str, rows_total: int):
        """Honestly increments rows_failed in the Job node."""
        cypher = """
        MERGE (j:Job {id: $job_id})
          ON CREATE SET j.dataset_id = $dataset_id,
                        j.status = 'loading',
                        j.rows_total = $rows_total,
                        j.rows_loaded = 0,
                        j.rows_failed = 1,
                        j.created_at = datetime(),
                        j.updated_at = datetime()
          ON MATCH SET j.rows_failed = j.rows_failed + 1,
                       j.status = CASE WHEN (j.rows_loaded + j.rows_failed + 1) >= j.rows_total THEN 'complete' ELSE 'loading' END,
                       j.updated_at = datetime()
        """
        try:
            with self._driver.session() as session:
                session.run(cypher, {
                    "job_id": job_id,
                    "dataset_id": dataset_id,
                    "rows_total": rows_total
                })
        except Exception as e:
            logger.error(f"Failed to record failure in Job node: {e}")

neo4j_writer = Neo4jWriter()
