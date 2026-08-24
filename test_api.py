from fastapi.testclient import TestClient
import time
from api_server import app, EXAM_STATE, db

client = TestClient(app)

def setup_module(module):
    db.clear()

def test_submit_questions():
    # First question
    resp1 = client.post("/api/v1/questions/submit", json={
        "question_text": "What is the capital of France?",
        "metadata": {"subject": "Geography"}
    })
    assert resp1.status_code == 200

    # Duplicate question
    resp2 = client.post("/api/v1/questions/submit", json={
        "question_text": "What is the capital of France??",
        "metadata": {"subject": "Geography"}
    })
    assert resp2.status_code == 400
    assert "rejected" in resp2.json()["detail"].lower()

def test_paper_generation():
    # Insert a few more distinct questions
    client.post("/api/v1/questions/submit", json={
        "question_text": "What is the largest ocean on Earth?",
        "metadata": {"subject": "Geography"}
    })
    client.post("/api/v1/questions/submit", json={
        "question_text": "Who wrote 'Hamlet'?",
        "metadata": {"subject": "Literature"}
    })
    client.post("/api/v1/questions/submit", json={
        "question_text": "What is the speed of light in a vacuum?",
        "metadata": {"subject": "Physics"}
    })

    # Request paper generation
    res = client.post("/api/v1/paper/generate", json={"num_questions": 3})
    assert res.status_code == 200
    
    paper_text = res.json()["paper_text"]
    assert "Confidential Exam Paper" in paper_text
    assert "Q1:" in paper_text
    assert "Q2:" in paper_text
    assert "Q3:" in paper_text

def test_encryption_and_unlock():
    # 1. Encrypt a paper, start time in future
    future_time = time.time() + 10 # 10 seconds in future
    enc_resp = client.post("/api/v1/paper/encrypt", json={
        "paper_text": "Confidential Exam Paper: Question 1...",
        "exam_start_time": future_time,
        "threshold_k": 3,
        "total_shares": 5
    })
    assert enc_resp.status_code == 200
    shares = enc_resp.json()["shares"]

    # 2. Try to unlock early - should fail
    unlock_resp = client.post("/api/v1/paper/unlock", json={
        "shares": shares[:3],
        "center_id": "CENTER_001",
        "session_token": "token_abc"
    })
    assert unlock_resp.status_code == 403
    
    # 3. Try to unlock with fewer shares - should fail
    # Update time to past so time gate passes
    EXAM_STATE["exam_start_time"] = time.time() - 10
    
    unlock_resp = client.post("/api/v1/paper/unlock", json={
        "shares": shares[:2],
        "center_id": "CENTER_001",
        "session_token": "token_abc"
    })
    assert unlock_resp.status_code == 403

    # 4. Success unlock
    unlock_resp = client.post("/api/v1/paper/unlock", json={
        "shares": shares[:3],
        "center_id": "CENTER_001",
        "session_token": "token_abc"
    })
    assert unlock_resp.status_code == 200
    paper_payload = unlock_resp.json()["paper_payload"]
    assert "Confidential Exam Paper" in paper_payload

    # 5. Trace watermark
    trace_resp = client.post("/api/v1/watermark/trace", json={
        "watermarked_payload": paper_payload
    })
    assert trace_resp.status_code == 200
    meta = trace_resp.json()["metadata"]
    assert meta["center_id"] == "CENTER_001"
    assert meta["session_token"] == "token_abc"
