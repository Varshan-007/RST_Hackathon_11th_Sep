import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver
from .config import settings

logger = logging.getLogger("api.neo4j")

class Neo4jClient:
    def __init__(self):
        self._driver: Optional[Driver] = None

    def connect(self) -> bool:
        try:
            if self._driver is None:
                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                    max_connection_lifetime=200,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=5.0
                )
            # Verify connectivity
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning(f"Neo4j connection check failed: {e}")
            self._driver = None
            return False

    def is_connected(self) -> bool:
        if self._driver is None:
            return self.connect()
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return self.connect()

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def execute_query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.is_connected():
            raise ConnectionError("Cannot connect to Neo4j database")
        
        with self._driver.session() as session:
            result = session.run(cypher, parameters or {})
            records = [record.data() for record in result]
            return records

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (j:Job {id: $job_id})
        RETURN j.id AS job_id,
               j.status AS status,
               j.rows_total AS rows_total,
               j.rows_loaded AS rows_loaded,
               j.rows_failed AS rows_failed
        """
        records = self.execute_query(cypher, {"job_id": job_id})
        if records:
            r = records[0]
            # Ensure types
            rows_total = int(r.get("rows_total") or 0)
            rows_loaded = int(r.get("rows_loaded") or 0)
            rows_failed = int(r.get("rows_failed") or 0)
            status = r.get("status") or "queued"

            if (rows_loaded + rows_failed) >= rows_total and rows_total > 0:
                status = "complete"

            return {
                "job_id": r.get("job_id"),
                "status": status,
                "rows_total": rows_total,
                "rows_loaded": rows_loaded,
                "rows_failed": rows_failed
            }
        return None

    def init_job(self, job_id: str, dataset_id: str, rows_total: int):
        cypher = """
        MERGE (j:Job {id: $job_id})
        SET j.dataset_id = $dataset_id,
            j.status = 'queued',
            j.rows_total = $rows_total,
            j.rows_loaded = 0,
            j.rows_failed = 0,
            j.created_at = datetime(),
            j.updated_at = datetime()
        """
        self.execute_query(cypher, {
            "job_id": job_id,
            "dataset_id": dataset_id,
            "rows_total": rows_total
        })

    def get_schema_summary(self) -> Dict[str, Any]:
        """Inspect dynamic schema of loaded Rows."""
        try:
            row_count_res = self.execute_query("MATCH (r:Row) RETURN count(r) AS count")
            row_count = row_count_res[0]["count"] if row_count_res else 0
            if row_count == 0:
                return {"row_count": 0, "properties": [], "sample_values": {}}

            # Get property keys of Row nodes
            props_res = self.execute_query("""
                MATCH (r:Row)
                WITH keys(r) AS k
                UNWIND k AS prop
                RETURN DISTINCT prop
            """)
            props = [p["prop"] for p in props_res if p["prop"] not in ["dataset_id", "row_index"]]

            # Get distinct sample values for categorical columns (up to 20 values per prop)
            sample_values = {}
            for prop in props[:15]:
                try:
                    val_res = self.execute_query(f"""
                        MATCH (r:Row)
                        WHERE r.{prop} IS NOT NULL
                        RETURN DISTINCT toString(r.{prop}) AS val
                        LIMIT 20
                    """)
                    sample_values[prop] = [v["val"] for v in val_res if v.get("val") is not None]
                except Exception:
                    pass

            return {
                "row_count": row_count,
                "properties": props,
                "sample_values": sample_values
            }
        except Exception as e:
            logger.warning(f"Error getting schema summary: {e}")
            return {"row_count": 0, "properties": [], "sample_values": {}}

neo4j_client = Neo4jClient()
