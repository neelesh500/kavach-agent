from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Tuple
import time
import os
import base64

from database_mock import DatabaseMock
from similarity_guard import SimilarityGuard
from crypto_core import CryptoManager, DoubleGateEnforcer
from watermark_engine import WatermarkEngine

app = FastAPI(title="Project Kavach Backend API")

db = DatabaseMock()
similarity_guard = SimilarityGuard(threshold=0.85)

# In-memory storage for exam keys and configuration (for demonstration purposes)
EXAM_STATE = {
    "exam_start_time": time.time() + 3600,  # 1 hour from now by default
    "threshold_k": 4,
    "total_shares": 7,
    "master_secret": None,
    "encrypted_paper": None,
    "shares": []
}

class QuestionPayload(BaseModel):
    question_text: str
    metadata: dict

class EncryptRequest(BaseModel):
    paper_text: str
    exam_start_time: float
    threshold_k: int
    total_shares: int

class UnlockRequest(BaseModel):
    shares: List[Tuple[int, int]]
    center_id: str
    session_token: str

class GeneratePaperRequest(BaseModel):
    num_questions: int

@app.post("/api/v1/questions/submit")
async def submit_question(payload: QuestionPayload):
    existing_questions = [q["text"] for q in db.get_questions()]
    
    if similarity_guard.is_duplicate(payload.question_text, existing_questions):
        db.log_audit("QUESTION_REJECTED", {"reason": "duplicate", "metadata": payload.metadata})
        raise HTTPException(status_code=400, detail="Question rejected: exceeds similarity threshold")
        
    db.add_question(payload.question_text, payload.metadata)
    db.log_audit("QUESTION_ACCEPTED", {"metadata": payload.metadata})
    return {"status": "success", "message": "Question accepted into pool"}

@app.post("/api/v1/paper/generate")
async def generate_paper(req: GeneratePaperRequest):
    questions = db.get_random_questions(req.num_questions)
    if len(questions) < req.num_questions:
        raise HTTPException(status_code=400, detail=f"Not enough questions in the database (found {len(questions)}, wanted {req.num_questions})")
        
    paper_lines = ["Confidential Exam Paper", "="*40]
    for i, q in enumerate(questions, start=1):
        paper_lines.append(f"Q{i}: {q['text']}")
        
    paper_text = "\n\n".join(paper_lines)
    db.log_audit("PAPER_GENERATED", {"num_questions": len(questions)})
    
    return {"status": "success", "paper_text": paper_text}

@app.post("/api/v1/paper/encrypt")
async def encrypt_paper(req: EncryptRequest):
    master_secret = int.from_bytes(os.urandom(32), byteorder='big') % CryptoManager.PRIME
    master_key = master_secret.to_bytes(32, byteorder='big')
    
    encrypted = CryptoManager.encrypt_payload(master_key, req.paper_text.encode())
    
    shares = CryptoManager.generate_shares(master_secret, req.total_shares, req.threshold_k)
    
    # Store state
    EXAM_STATE["exam_start_time"] = req.exam_start_time
    EXAM_STATE["threshold_k"] = req.threshold_k
    EXAM_STATE["total_shares"] = req.total_shares
    EXAM_STATE["master_secret"] = master_secret
    EXAM_STATE["encrypted_paper"] = encrypted
    EXAM_STATE["shares"] = shares
    
    shares_str = [(str(x), str(y)) for x, y in shares]
    
    return {
        "status": "success",
        "shares": shares_str,
        "message": f"Generated {req.total_shares} shares with threshold {req.threshold_k}"
    }

@app.post("/api/v1/paper/unlock")
async def unlock_paper(req: UnlockRequest):
    gate = DoubleGateEnforcer(EXAM_STATE["exam_start_time"], EXAM_STATE["threshold_k"])
    current_time = time.time()
    
    if not gate.can_unlock(current_time, len(req.shares)):
        db.log_audit("UNAUTHORIZED_UNLOCK", {"center_id": req.center_id, "shares_count": len(req.shares)})
        raise HTTPException(status_code=403, detail="Double-Gate violation: Either early attempt or insufficient shares")
        
    try:
        secret = CryptoManager.reconstruct_secret(req.shares, EXAM_STATE["threshold_k"])
        key = secret.to_bytes(32, byteorder='big')
        decrypted = CryptoManager.decrypt_payload(key, EXAM_STATE["encrypted_paper"]).decode()
        
        # Watermark the paper for this specific center
        watermarked_paper = WatermarkEngine.embed_watermark(decrypted, req.center_id, req.session_token)
        
        db.log_audit("PAPER_UNLOCKED", {"center_id": req.center_id})
        return {"paper_payload": watermarked_paper}
        
    except Exception as e:
        db.log_audit("UNLOCK_FAILED", {"center_id": req.center_id, "error": str(e)})
        raise HTTPException(status_code=400, detail="Failed to reconstruct key or decrypt payload. Shares may be invalid.")

class TraceRequest(BaseModel):
    watermarked_payload: str

@app.post("/api/v1/watermark/trace")
async def trace_watermark(req: TraceRequest):
    metadata = WatermarkEngine.extract_watermark(req.watermarked_payload)
    if not metadata:
        raise HTTPException(status_code=404, detail="No watermark found in payload")
    return {"metadata": metadata}

@app.get("/api/v1/paper/fetch_encrypted")
async def fetch_encrypted():
    if not EXAM_STATE.get("encrypted_paper"):
        raise HTTPException(status_code=404, detail="No paper encrypted yet")
    return {
        "encrypted_paper": base64.b64encode(EXAM_STATE["encrypted_paper"]).decode('utf-8'),
        "threshold_k": EXAM_STATE["threshold_k"],
        "exam_start_time": EXAM_STATE["exam_start_time"]
    }

