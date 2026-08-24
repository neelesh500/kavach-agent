import time
from api_server import EXAM_STATE, db
from fastapi.testclient import TestClient
from api_server import app

client = TestClient(app)

def run():
    db.clear()
    print("Testing submit questions...")
    resp1 = client.post("/api/v1/questions/submit", json={
        "question_text": "What is the capital of France?",
        "metadata": {"subject": "Geography"}
    })
    print("resp1:", resp1.status_code, resp1.json())
    resp2 = client.post("/api/v1/questions/submit", json={
        "question_text": "What is the capital city of France?",
        "metadata": {"subject": "Geography"}
    })
    print("resp2:", resp2.status_code, resp2.json())

    print("\nTesting encryption and unlock...")
    future_time = time.time() + 10
    enc_resp = client.post("/api/v1/paper/encrypt", json={
        "paper_text": "Confidential Examp Paper: Question 1...",
        "exam_start_time": future_time,
        "threshold_k": 3,
        "total_shares": 5
    })
    shares = enc_resp.json()["shares"]
    print("enc_resp:", enc_resp.status_code, "shares:", shares)
    
    print("Master secret:", EXAM_STATE["master_secret"])
    from crypto_core import CryptoManager
    rec = CryptoManager.reconstruct_secret(shares[:3], 3)
    print("Reconstructed secret:", rec)
    print("Equals?", EXAM_STATE["master_secret"] == rec)
    
    EXAM_STATE["exam_start_time"] = time.time() - 10
    
    unlock_resp = client.post("/api/v1/paper/unlock", json={
        "shares": shares[:3],
        "center_id": "CENTER_001",
        "session_token": "token_abc"
    })
    print("unlock_resp:", unlock_resp.status_code, unlock_resp.json())

if __name__ == "__main__":
    run()
