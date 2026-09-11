import csv
import io
import uuid
import hashlib
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .models import IngestResponse, StatusResponse, HealthResponse, ChatRequest, ChatResponse
from .kafka_producer import kafka_producer
from .neo4j_client import neo4j_client
from .chatbot import chatbot_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api")

app = FastAPI(title="Data In, Answers Out API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory fast cache for active jobs
active_jobs = {}

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing API connections to Kafka and Neo4j...")
    kafka_producer.connect(retries=5, delay=2.0)
    neo4j_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Closing API connections...")
    kafka_producer.close()
    neo4j_client.close()

@app.get("/health", response_model=HealthResponse)
def get_health(response: Response):
    kafka_ok = kafka_producer.is_connected()
    neo4j_ok = neo4j_client.is_connected()
    
    is_ok = kafka_ok and neo4j_ok
    if not is_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="not ok",
            kafka_connected=kafka_ok,
            neo4j_connected=neo4j_ok
        )

    return HealthResponse(
        status="ok",
        kafka_connected=True,
        neo4j_connected=True
    )

@app.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_csv(file: UploadFile = File(...)):
    # 1. Validate file extension / mime
    filename = file.filename or "uploaded.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV files (.csv) are supported."
        )

    # 2. Read file content
    try:
        content_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    # 3. Check for empty file
    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty (0 bytes)."
        )

    # 4. Decode content
    try:
        content_text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content_text = content_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File encoding error. Please provide a valid UTF-8 encoded CSV file."
            )

    # 5. Parse CSV
    try:
        reader = list(csv.reader(io.StringIO(content_text)))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed CSV syntax: {str(e)}"
        )

    # Remove empty lines
    reader = [row for row in reader if row and any(cell.strip() for cell in row)]

    if len(reader) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file contains no data."
        )

    headers = [h.strip() for h in reader[0]]
    data_rows = reader[1:]

    # 6. Check for header-only CSV
    if len(data_rows) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains a header row but zero data rows."
        )

    total_rows = len(data_rows)

    # 7. Generate deterministic dataset_id & job_id
    # Hash of the normalized content ensures reproducible dataset_id
    dataset_id = hashlib.sha256(content_bytes).hexdigest()[:12]
    job_id = uuid.uuid4().hex[:8]

    # 8. Record Job in Neo4j & in-memory cache
    active_jobs[job_id] = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "queued",
        "rows_total": total_rows,
        "rows_loaded": 0,
        "rows_failed": 0
    }

    try:
        neo4j_client.init_job(job_id=job_id, dataset_id=dataset_id, rows_total=total_rows)
    except Exception as e:
        logger.warning(f"Could not immediately init job in Neo4j (will rely on loader): {e}")

    # 9. Stream rows into Kafka
    kafka_messages = []
    for idx, row in enumerate(data_rows, start=1):
        # Create dict mapping header to value
        row_dict = {}
        for h_idx, header in enumerate(headers):
            val = row[h_idx].strip() if h_idx < len(row) else ""
            # Try type coercion for numbers
            if val.isdigit():
                row_dict[header] = int(val)
            else:
                try:
                    row_dict[header] = float(val) if ("." in val and len(val) < 20) else val
                except ValueError:
                    row_dict[header] = val

        kafka_messages.append({
            "job_id": job_id,
            "dataset_id": dataset_id,
            "filename": filename,
            "row_index": idx,
            "rows_total": total_rows,
            "data": row_dict
        })

    try:
        kafka_producer.send_batch(settings.kafka_topic, kafka_messages)
    except Exception as e:
        logger.error(f"Failed to publish messages to Kafka: {e}")
        active_jobs[job_id]["status"] = "failed"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish data to Kafka topic: {str(e)}"
        )

    return IngestResponse(
        job_id=job_id,
        rows_received=total_rows,
        status="queued"
    )

@app.get("/status", response_model=StatusResponse)
def get_job_status(job_id: str = Query(..., description="The ID of the ingestion job")):
    # Check Neo4j first
    try:
        db_status = neo4j_client.get_job_status(job_id)
        if db_status:
            return StatusResponse(**db_status)
    except Exception as e:
        logger.warning(f"Error reading job status from Neo4j: {e}")

    # Fallback to in-memory active jobs
    if job_id in active_jobs:
        return StatusResponse(**active_jobs[job_id])

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Job with ID '{job_id}' not found."
    )

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    response_data = chatbot_engine.process_question(request.question)
    return ChatResponse(**response_data)
