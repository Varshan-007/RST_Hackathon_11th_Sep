# Data In, Answers Out — CSV → Kafka → Neo4j → Chatbot Pipeline

A complete, production-grade 5-container architecture streaming any CSV file through Kafka into Neo4j with idempotent graph ingestion, live progress tracking, strict API contract enforcement, and a grounded natural language chatbot interface.

---

## 🏗️ Architecture

```
Browser (UI on :3000)
  │  Drag-and-Drop CSV · Live Progress · Grounded Chat
  ▼
 [ui] (React + Vite + Nginx, non-root, port 3000)
  │  POST /ingest, GET /status, POST /chat, GET /health
  ▼
 [api] (FastAPI, Python 3.11-slim, non-root, port 8000)
  │  - POST /ingest  → validate, compute dataset_id hash, produce to Kafka, return 202
  │  - GET  /status  → query true load progress from Neo4j Job node
  │  - POST /chat    → schema-aware NL-to-Cypher engine with truthful grounding
  │  - GET  /health  → 200/503 checking real Kafka broker & Neo4j Bolt connectivity
  │
  ├── produces to Kafka topic "csv-rows"
  ▼
 [kafka] (apache/kafka:3.7.0, KRaft mode, port 9092)
  │
  ├── consumed by loader
  ▼
 [loader] (Python 3.11-slim, non-root consumer)
  │  - Consumes "csv-rows" with automatic reconnection & retry-with-backoff
  │  - MERGEs (:Dataset) and (:Row) idempotently via official Neo4j Bolt driver
  │  - Updates (:Job) node with rows_loaded and rows_failed in real-time
  ▼
 [neo4j] (neo4j:5.24-community, port 7687 / 7474)
  Graph Schema:
  (:Dataset {id, filename, uploaded_at, row_count})
    -[:HAS_ROW]->
  (:Row {dataset_id, row_index, ...dynamic_csv_columns})
  (:Job {id, dataset_id, status, rows_total, rows_loaded, rows_failed, updated_at})
```

---

## 🚀 Quick Start (Zero Manual Steps)

### 1. Start all 5 services
```bash
docker compose up -d --build
```

### 2. Verify health status
```bash
curl http://localhost:8000/health
# Response: {"status":"ok","kafka_connected":true,"neo4j_connected":true}
```

### 3. Open the UI
Visit **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 📡 API Interface Contract

### `POST /ingest`
Uploads a CSV file for asynchronous streaming ingestion into Kafka.
```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@test_data/small_clean.csv"
```
**Response (`202 Accepted`):**
```json
{
  "job_id": "8f3d1a2b",
  "rows_received": 20,
  "status": "queued"
}
```

### `GET /status?job_id=<job_id>`
Retrieves honest real-time progress of ingestion from the graph database.
```bash
curl "http://localhost:8000/status?job_id=8f3d1a2b"
```
**Response (`200 OK`):**
```json
{
  "job_id": "8f3d1a2b",
  "status": "complete",
  "rows_total": 20,
  "rows_loaded": 20,
  "rows_failed": 0
}
```

### `POST /chat`
Asks a natural language question about the ingested dataset.
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many rows belong to the Billing group?"}'
```
**Response (`200 OK`):**
```json
{
  "answer": "There are 5 rows where department = 'Billing'.",
  "cypher": "MATCH (r:Row) WHERE toLower(toString(r.department)) = 'billing' RETURN count(r) AS count",
  "result": [
    {
      "count": 5
    }
  ],
  "grounded": true
}
```

**Ungrounded Example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is the president of France?"}'
```
**Response (`200 OK`):**
```json
{
  "answer": "I don't have that in the data. The uploaded dataset contains 20 rows with properties: id, name, department, role, salary, city, status.",
  "cypher": "MATCH (r:Row) RETURN keys(r) AS properties LIMIT 1",
  "result": [...],
  "grounded": false
}
```

---

## 🧪 Test Datasets & Hostile Input Checklist

| File | Purpose | Expected Behavior |
|------|---------|-------------------|
| `test_data/small_clean.csv` | 20 clean rows | Ingests in <1s, 100% loaded |
| `test_data/medium_volume.csv` | 1,000 rows volume test | Streaming progress bar, fast throughput |
| `test_data/broken_ragged.csv` | Ragged lines, missing columns | Graceful failure counting, no crash |
| `test_data/empty.csv` | 0-byte file | 400 Bad Request: "Uploaded CSV file is empty" |
| `test_data/header_only.csv` | Headers only, 0 data rows | 400 Bad Request: "CSV contains headers but zero data rows" |
| `test_data/not_a_csv.txt` | Non-CSV file | 400 Bad Request: "Invalid file format" |

---

## 🔒 Security & Container Hygiene

- **All Base Images Pinned**:
  - `apache/kafka:3.7.0`
  - `neo4j:5.24-community`
  - `python:3.11-slim`
  - `node:20-alpine`
  - `nginx:1.27-alpine`
- **Non-Root Execution**: `appuser` (UID 1000) for `api` and `loader`, `nginx` for `ui`.
- **Zero Hardcoded Secrets**: Credentials managed via environment variables.
- **Idempotent Storage**: Repeated uploads of the exact same CSV will `MERGE` existing records without duplicate node creation.

---

## 🛑 Teardown
```bash
docker compose down -v
```
