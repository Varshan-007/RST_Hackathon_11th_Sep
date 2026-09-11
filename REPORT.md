# Project Report — Data In, Answers Out
**Event**: RISE @ RST Hackathon #5  
**System Name**: Data In, Answers Out (CSV → Kafka → Neo4j → Grounded Chatbot Pipeline)  
**Date**: September 2026  

---

## 9.1 What We Built

We built a containerized 5-service pipeline that streams arbitrary CSV uploads into a Neo4j graph database via Apache Kafka and serves grounded natural language question-answering on top of it. When a user uploads a CSV file through the UI or API, the API validates the file, hashes the content to create a deterministic dataset identifier, and immediately streams rows to a KRaft Kafka broker before returning an asynchronous `202 Accepted` response. A dedicated loader service consumes messages from Kafka, merges nodes and relationships idempotently into Neo4j via the official Bolt driver, and records real-time load progress directly in a database tracking node. The chatbot answers questions strictly by executing dynamic Cypher queries against the graph and truthfully admits `grounded: false` whenever the question cannot be backed by graph data. The entire pipeline boots in a single command (`docker compose up -d`) with pinned images, non-root security, real readiness health checks, and zero manual setup steps.

```
Browser UI (:3000) ──► FastAPI (:8000) ──► Kafka (:9092) ──► Loader ──► Neo4j (:7687)
         │                     ▲                                              │
         └─────────────────────┴────── Cypher Graph Query & Grounded Chat ────┘
```

---

## 9.2 The Data and the Graph Model

### Test Datasets Used
1. **`small_clean.csv`** (20 rows, 7 columns): `id`, `name`, `department`, `role`, `salary`, `city`, `status`. Sanity-checked end-to-end flow, exact property indexing, and multi-filter chatbot queries.
2. **`medium_volume.csv`** (1,000 rows, 7 columns): Volume and throughput testing with dynamic role distributions, numeric ranges, and live progress bar polling.
3. **`broken_ragged.csv`** (4 rows with mismatched columns and unclosed quotes): Verified error handling and honest `rows_failed` counter incrementation.
4. **`empty.csv`** (0 bytes): Verified instant rejection with `400 Bad Request`.
5. **`header_only.csv`** (1 row header, 0 data rows): Verified rejection with `400 Bad Request`.
6. **`not_a_csv.txt`** (plain text): Verified file validation and MIME rejection with `400 Bad Request`.

### Graph Schema Produced in Neo4j
- **Labels**:
  - `(:Dataset)`: Represents an uploaded file.
    - Properties: `id` (deterministic SHA-256 hash), `filename` (string), `uploaded_at` (datetime), `row_count` (integer).
  - `(:Row)`: Represents each individual row in the CSV.
    - Properties: `dataset_id` (string), `row_index` (integer), plus dynamic flat properties mapped directly from the CSV headers (e.g. `name`, `department`, `role`, `salary`, `city`, `status`). Numeric strings are automatically cast to integers or floats for arithmetic Cypher aggregations.
  - `(:Job)`: Real-time tracking node queried by `GET /status`.
    - Properties: `id` (string), `dataset_id` (string), `status` (`queued | loading | complete | failed`), `rows_total` (int), `rows_loaded` (int), `rows_failed` (int), `created_at` (datetime), `updated_at` (datetime).
- **Relationships**:
  - `(:Dataset)-[:HAS_ROW]->(:Row)`: Strict 1-to-N hierarchy between dataset and constituent records.

---

## 9.3 Methods

| Decision | Chosen | Rejected | Reason |
| :--- | :--- | :--- | :--- |
| **Ingest path** | Asynchronous streaming via Kafka topic (`csv-rows`) | Direct API-to-Neo4j write or synchronous database insertion | Decouples file upload acceptance from graph database write latency; allows queueing during database spikes or transient outages; enables topic replay without requiring file re-upload. |
| **Idempotency key** | Composite key of `(dataset_id + row_index)` where `dataset_id = sha256(content)[:12]` | Autoincrementing IDs or random UUIDs per row | Guarantees that repeating an upload of the exact same CSV executes `MERGE` against existing nodes without creating duplicate rows or inflating node counts. |
| **Chatbot approach** | Schema-aware natural language to Cypher translation engine with 12+ intent templates and fallback ungrounded detection | General LLM generation with direct knowledge answering | Strict guarantee against hallucination; enforces requirement that every response executes a live Cypher query against Neo4j and returns raw graph records with explicit `grounded: true/false`. |
| **How API knows Kafka/Neo4j are ready** | Active readiness probes with retry-with-backoff loops and Docker `healthcheck` `service_healthy` conditions | Plain Docker `depends_on` without health checks | `depends_on` only checks container process start, not broker leader election or Neo4j Bolt port readiness. Probing ensures `/health` returns `not ok` until both services accept queries. |

---

## 9.4 Results

| Question Asked | Answer Given | Correct? | Grounded? |
| :--- | :--- | :---: | :---: |
| **"How many rows in total?"** | `There are 20 total rows in the dataset.` | Yes | Grounded ✅ |
| **"How many rows belong to the Billing group?"** | `There are 5 rows where department = 'Billing'.` | Yes | Grounded ✅ |
| **"What are the unique departments?"** | `The 5 distinct values for 'department' are: Billing, Engineering, Marketing, Sales, Support.` | Yes | Grounded ✅ |
| **"List all roles"** | `The 14 distinct values for 'role' are: Account Executive, Billing Analyst, Billing Specialist, Content Strategist, DevOps Engineer...` | Yes | Grounded ✅ |
| **"What columns are in the dataset?"** | `The dataset contains columns: city, department, id, name, role, salary, status.` | Yes | Grounded ✅ |
| **"How many rows per department?"** | `Distribution for 'department': Engineering: 6, Billing: 5, Marketing: 3, Sales: 3, Support: 3.` | Yes | Grounded ✅ |
| **"Show row 5"** | `Row 5 details: id: 5, name: Emma Davis, department: Billing, role: Billing Analyst, salary: 75000, city: Chicago, status: active, row_index: 5` | Yes | Grounded ✅ |
| **"What is the average salary?"** | `The avg of 'salary' is 92100.00.` | Yes | Grounded ✅ |
| **"Who is the president of France?"** | `I don't have that in the data. The uploaded dataset contains 20 rows with properties: city, department, id, name, role, salary, status.` | Yes | Not Grounded ⚠️ |
| **"What is the weather in Tokyo tomorrow?"** | `I don't have that in the data. The uploaded dataset contains 20 rows with properties: city, department, id, name, role, salary, status.` | Yes | Not Grounded ⚠️ |

### Interpretation of Results
The grounded query engine correctly matched all domain-relevant schema questions (counts, categorical filters, breakdowns, lookups, column inspection, and arithmetic averages) directly to optimized Cypher queries. When questioned about external knowledge not represented in the CSV schema (e.g. world leaders, weather), the engine detected the absence of matching properties, executed a safety inspection query, and explicitly returned `grounded: false` alongside an honest refusal message.

---

## 9.5 How We Worked

### Roles & Execution
- **Pipeline Architecture & Orchestration**: Designed KRaft single-broker Kafka orchestration, Neo4j multi-container networking, healthchecks, and non-root execution.
- **Backend API & Ingestion Engine**: Built FastAPI endpoints (`/ingest`, `/status`, `/health`, `/chat`), input validation, and asynchronous Kafka batching.
- **Loader & Graph Modeling**: Built Bolt consumer with transactional `MERGE` idempotency, real-time `:Job` tracking, and failure handling.
- **Frontend Experience**: Built React + Vite glassmorphic SPA with drag-and-drop ingestion, instant client-side preview, live status polling, and collapsible Cypher result inspector.

### Key Architectural Decisions

1. **Decision**: Deterministic Content Hashing for `dataset_id`
   - *Options considered*: Random UUID per upload vs Filename string vs Content SHA-256.
   - *Chosen because*: SHA-256 of file content guarantees that identical files result in the exact same dataset key across separate upload calls.
   - *Cost accepted*: Slight computation overhead during ingest hash calculation.
   - *Would revisit if*: Uploads were multi-gigabyte streams where streaming hash chunking would be preferred over full in-memory hashing.

2. **Decision**: Status Tracking Directly Inside Neo4j `:Job` Nodes
   - *Options considered*: In-memory API dictionary vs Redis queue vs Neo4j Job node.
   - *Chosen because*: Writing job progress (`rows_loaded`, `rows_failed`, `status`) to Neo4j ensures that API instances can be restarted without losing track of ongoing ingestion progress.
   - *Cost accepted*: Small overhead of updating `:Job` properties in the consumer loop.
   - *Would revisit if*: Processing > 1,000,000 events/sec, where Redis or Kafka consumer lag metrics would be used instead of database-level status writes.

### Dead End Encountered
Initially, we considered relying on standard Neo4j APOC triggers for background loading from Kafka. However, configuring APOC extensions across heterogeneous community Docker images introduced startup synchronization race conditions. We quickly abandoned this approach in favor of a dedicated Python consumer (`loader`) with explicit retry-with-backoff loops and non-root process supervision, giving full deterministic control over failure tracking and idempotency.

---

## 9.6 Limitations and Next Steps

1. **Schema Evolution on Re-upload**:
   If a user uploads a modified version of a CSV with the exact same content except for an altered header name, the current system merges new properties into existing `Row` nodes rather than dropping obsolete columns. A future iteration could support explicit `REPLACE` or `UPSERT` semantics.
2. **Kafka Partition Scaling**:
   The current setup uses a single topic partition for strict in-order processing. To scale to millions of rows per second, partitioning on `dataset_id` would allow multiple parallel loader containers while maintaining per-dataset idempotency.
3. **Complex Multi-Hop Natural Language Reasoning**:
   The rule-based NL-to-Cypher engine covers 12 standard query patterns with 100% determinism. For open-ended natural language questions spanning multi-hop joins across 5+ tables, an optional locally-hosted LLM (e.g. Ollama with Llama 3) could augment the template engine.

---

## 9.7 How to Run It

### 1. Start all 5 services
```bash
docker compose down -v && docker compose up -d --build
```

### 2. Verify health
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","kafka_connected":true,"neo4j_connected":true}
```

### 3. Ingest a test CSV
```bash
curl -X POST http://localhost:8000/ingest -F "file=@test_data/small_clean.csv"
```

### 4. Poll status
```bash
curl "http://localhost:8000/status?job_id=<JOB_ID_FROM_STEP_3>"
```

### 5. Query the chatbot
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many rows belong to the Billing group?"}'
```

### 6. Open the Web UI
Navigate to **[http://localhost:3000](http://localhost:3000)**.
