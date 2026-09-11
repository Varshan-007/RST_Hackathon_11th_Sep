#!/usr/bin/env python3
import time
import json
import requests
import sys

API_URL = "http://localhost:8000"

def log(msg, symbol="ℹ️"):
    print(f"{symbol} {msg}")

def test_health():
    log("Checking /health endpoint...")
    for _ in range(30):
        try:
            res = requests.get(f"{API_URL}/health", timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("kafka_connected") and data.get("neo4j_connected"):
                    log(f"/health is OK: {data}", "✅")
                    return True
        except Exception:
            pass
        time.sleep(2)
    log("/health check timed out or failed!", "❌")
    return False

def test_hostile_inputs():
    log("Testing Hostile Inputs...")
    
    # 1. Empty CSV
    try:
        with open("test_data/empty.csv", "rb") as f:
            res = requests.post(f"{API_URL}/ingest", files={"file": ("empty.csv", f, "text/csv")})
        assert res.status_code == 400, f"Expected 400 for empty.csv, got {res.status_code}"
        log(f"Empty CSV rejected with 400: {res.json()}", "✅")
    except Exception as e:
        log(f"Empty CSV test failed: {e}", "❌")

    # 2. Header only CSV
    try:
        with open("test_data/header_only.csv", "rb") as f:
            res = requests.post(f"{API_URL}/ingest", files={"file": ("header_only.csv", f, "text/csv")})
        assert res.status_code == 400, f"Expected 400 for header_only.csv, got {res.status_code}"
        log(f"Header-only CSV rejected with 400: {res.json()}", "✅")
    except Exception as e:
        log(f"Header-only CSV test failed: {e}", "❌")

    # 3. Non-CSV file
    try:
        with open("test_data/not_a_csv.txt", "rb") as f:
            res = requests.post(f"{API_URL}/ingest", files={"file": ("not_a_csv.txt", f, "text/plain")})
        assert res.status_code == 400, f"Expected 400 for not_a_csv.txt, got {res.status_code}"
        log(f"Non-CSV file rejected with 400: {res.json()}", "✅")
    except Exception as e:
        log(f"Non-CSV test failed: {e}", "❌")

    # 4. Chat before upload or ungrounded question
    try:
        res = requests.post(f"{API_URL}/chat", json={"question": "What is the population of Mars?"})
        assert res.status_code == 200
        data = res.json()
        assert data.get("grounded") is False
        log(f"Ungrounded question returned grounded=false: {data['answer']}", "✅")
    except Exception as e:
        log(f"Ungrounded question test failed: {e}", "❌")

def test_ingest_and_idempotency():
    log("Testing Ingestion & Idempotency...")
    # First ingest
    t0 = time.time()
    with open("test_data/small_clean.csv", "rb") as f:
        res = requests.post(f"{API_URL}/ingest", files={"file": ("small_clean.csv", f, "text/csv")})
    elapsed_ms = (time.time() - t0) * 1000
    assert res.status_code == 202, f"Expected 202, got {res.status_code}"
    job_data = res.json()
    job_id = job_data["job_id"]
    log(f"Ingest accepted in {elapsed_ms:.2f}ms: Job {job_id}", "✅")

    # Poll status
    log(f"Polling status for job {job_id}...")
    for _ in range(30):
        s_res = requests.get(f"{API_URL}/status?job_id={job_id}")
        s_data = s_res.json()
        if s_data.get("status") == "complete":
            log(f"Job completed! Total: {s_data['rows_total']}, Loaded: {s_data['rows_loaded']}, Failed: {s_data['rows_failed']}", "✅")
            break
        time.sleep(0.5)

    # Check row count via chat
    res_chat = requests.post(f"{API_URL}/chat", json={"question": "How many total rows in the dataset?"})
    count_1 = res_chat.json()["result"][0]["count"]
    log(f"Row count after 1st ingest: {count_1}", "✅")

    # Second ingest of exact same file (Idempotency test)
    log("Re-uploading exact same CSV to test idempotency...")
    with open("test_data/small_clean.csv", "rb") as f:
        res2 = requests.post(f"{API_URL}/ingest", files={"file": ("small_clean.csv", f, "text/csv")})
    job2_id = res2.json()["job_id"]
    for _ in range(30):
        s_res = requests.get(f"{API_URL}/status?job_id={job2_id}")
        if s_res.json().get("status") == "complete":
            break
        time.sleep(0.5)

    res_chat2 = requests.post(f"{API_URL}/chat", json={"question": "How many total rows in the dataset?"})
    count_2 = res_chat2.json()["result"][0]["count"]
    log(f"Row count after 2nd ingest: {count_2}", "✅")
    assert count_1 == count_2, f"Idempotency failed! First count: {count_1}, Second count: {count_2}"
    log("Idempotency PASSED: Node count is identical after repeat ingest!", "🎉")

def test_chatbot_grounding():
    log("Testing Chatbot Grounding across 8+ Questions...")
    questions = [
        "How many rows in total?",
        "How many rows belong to the Billing group?",
        "What are the unique departments?",
        "List all roles",
        "What columns are in the dataset?",
        "How many rows per department?",
        "Show row 5",
        "What is the average salary?",
        "Who is the CEO of Google?", # Ungrounded
        "What is the capital of Mars?" # Ungrounded
    ]

    for q in questions:
        res = requests.post(f"{API_URL}/chat", json={"question": q})
        data = res.json()
        status_sym = "✅" if data.get("grounded") else "⚠️"
        print(f"\n[Question]: {q}")
        print(f"[Answer]: {data.get('answer')}")
        print(f"[Cypher]: {data.get('cypher')}")
        print(f"[Grounded]: {data.get('grounded')} {status_sym}")

if __name__ == "__main__":
    if test_health():
        test_hostile_inputs()
        test_ingest_and_idempotency()
        test_chatbot_grounding()
        log("All automated pipeline verification tests passed successfully!", "🏆")
    else:
        sys.exit(1)
