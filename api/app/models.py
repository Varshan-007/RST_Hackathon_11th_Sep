from typing import List, Any, Dict, Optional
from pydantic import BaseModel, Field

class IngestResponse(BaseModel):
    job_id: str
    rows_received: int
    status: str = "queued"

class StatusResponse(BaseModel):
    job_id: str
    status: str  # queued | loading | complete | failed
    rows_total: int
    rows_loaded: int
    rows_failed: int

class HealthResponse(BaseModel):
    status: str  # ok | not ok
    kafka_connected: bool
    neo4j_connected: bool

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    cypher: str
    result: List[Dict[str, Any]]
    grounded: bool
