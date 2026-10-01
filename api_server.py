from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple
import time
import os
import base64

from database_mock import DatabaseMock
from similarity_guard import SimilarityGuard
from crypto_core import CryptoManager, DoubleGateEnforcer
from watermark_engine import WatermarkEngine
from ai_engine import ZEEAAIEngine


app = FastAPI(title="Project Kavach Backend API")

# Setup CORS to allow extension popup to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (including chrome-extension://)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Use SQLite Mock DB instead of MongoDB to run locally without setup
db = DatabaseMock()

# Similarity checker
similarity_guard = SimilarityGuard(threshold=0.85)

# AI Engine for Blueprint Generation
ai_engine = ZEEAAIEngine()


# ---------------------------------------------------------
# MongoDB startup connection check
# ---------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    pass


# ---------------------------------------------------------
# In-memory storage for exam keys and configuration
# ---------------------------------------------------------

EXAM_STATE = {
    "exam_start_time": time.time() + 3600,  # 1 hour from now by default
    "threshold_k": 4,
    "total_shares": 7,
    "master_secret": None,
    "encrypted_paper": None,
    "shares": []
}


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

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


class TraceRequest(BaseModel):
    watermarked_payload: str


# ---------------------------------------------------------
# Submit Question
# ---------------------------------------------------------

@app.post("/api/v1/questions/submit")
async def submit_question(payload: QuestionPayload):

    # Get all existing questions from MongoDB
    existing_questions = [
        q["text"]
        for q in db.get_questions()
    ]

    # Check whether the question is a duplicate
    if similarity_guard.is_duplicate(
        payload.question_text,
        existing_questions
    ):

        # Store rejection in audit logs
        db.log_audit(
            "QUESTION_REJECTED",
            {
                "reason": "duplicate",
                "metadata": payload.metadata
            }
        )

        raise HTTPException(
            status_code=400,
            detail="Question rejected: exceeds similarity threshold"
        )

    # Add question to MongoDB
    db.add_question(
        payload.question_text,
        payload.metadata
    )

    # Store acceptance in audit logs
    db.log_audit(
        "QUESTION_ACCEPTED",
        {
            "metadata": payload.metadata
        }
    )

    return {
        "status": "success",
        "message": "Question accepted into pool"
    }


# ---------------------------------------------------------
# Generate Exam Paper
# ---------------------------------------------------------

@app.post("/api/v1/paper/generate")
async def generate_paper(req: GeneratePaperRequest):
    # Get questions up to requested number limit
    final_questions = db.get_random_questions(req.num_questions)

    if not final_questions:
        raise HTTPException(status_code=400, detail="Database is empty. Seed questions first.")

    # Create exam paper
    paper_lines = [
        "====== CONFIDENTIAL EXAM PAPER ======",
        f"Generated Questions: {len(final_questions)} | Secure Exam Environment",
        "=" * 54
    ]
    
    current_subject = ""
    for i, q in enumerate(final_questions, start=1):
        meta = q.get("metadata", {})
        subj = meta.get("subject", "General")
        diff = meta.get("difficulty", "Medium")
        
        # Add Subject Headers to make it look professional
        if subj != current_subject:
            paper_lines.append(f"\n--- SECTION: {subj.upper()} ---")
            current_subject = subj
            
        paper_lines.append(f"\nQ{i}. [{diff}] {q['text']}")
        
        options = meta.get("options", [])
        if options:
            for idx, opt in enumerate(options):
                # mapping 0,1,2,3 to A,B,C,D
                letter = chr(65 + idx)
                paper_lines.append(f"   {letter}) {opt}")
        else:
            # If no options, provide a blank space for subjective answers
            paper_lines.append("\n   Answer: ______________________________\n")

    paper_text = "\n".join(paper_lines)

    db.log_audit("PAPER_GENERATED_VIA_AI", {"num_questions": len(final_questions)})

    return {
        "status": "success",
        "paper_text": paper_text
    }




# ---------------------------------------------------------
# Encrypt Exam Paper
# ---------------------------------------------------------

@app.post("/api/v1/paper/encrypt")
async def encrypt_paper(req: EncryptRequest):

    # Generate master secret
    master_secret = (
        int.from_bytes(
            os.urandom(32),
            byteorder="big"
        )
        % CryptoManager.PRIME
    )

    # Convert secret to encryption key
    master_key = master_secret.to_bytes(
        32,
        byteorder="big"
    )

    # Encrypt paper
    encrypted = CryptoManager.encrypt_payload(
        master_key,
        req.paper_text.encode()
    )

    # Generate secret shares
    shares = CryptoManager.generate_shares(
        master_secret,
        req.total_shares,
        req.threshold_k
    )

    # Store exam state
    EXAM_STATE["exam_start_time"] = req.exam_start_time
    EXAM_STATE["threshold_k"] = req.threshold_k
    EXAM_STATE["total_shares"] = req.total_shares
    EXAM_STATE["master_secret"] = master_secret
    EXAM_STATE["encrypted_paper"] = encrypted
    EXAM_STATE["shares"] = shares
    # Send shares as strings to avoid JS double-precision dataloss
    shares_str = [[str(x), str(y)] for x, y in shares]

    return {
        "status": "success",
        "shares": shares_str,
        "message": (
            f"Generated {req.total_shares} shares "
            f"with threshold {req.threshold_k}"
        )
    }


# ---------------------------------------------------------
# Unlock Exam Paper
# ---------------------------------------------------------

@app.post("/api/v1/paper/unlock")
async def unlock_paper(req: UnlockRequest):

    gate = DoubleGateEnforcer(
        EXAM_STATE["exam_start_time"],
        EXAM_STATE["threshold_k"]
    )

    current_time = time.time()

    # Check double-gate conditions
    if not gate.can_unlock(
        current_time,
        len(req.shares)
    ):

        db.log_audit(
            "UNAUTHORIZED_UNLOCK",
            {
                "center_id": req.center_id,
                "shares_count": len(req.shares)
            }
        )

        raise HTTPException(
            status_code=403,
            detail=(
                "Double-Gate violation: "
                "Either early attempt or insufficient shares"
            )
        )

    try:

        # Reconstruct secret
        secret = CryptoManager.reconstruct_secret(
            req.shares,
            EXAM_STATE["threshold_k"]
        )

        # Convert secret to key
        key = secret.to_bytes(
            32,
            byteorder="big"
        )

        # Decrypt paper
        decrypted = CryptoManager.decrypt_payload(
            key,
            EXAM_STATE["encrypted_paper"]
        ).decode()

        # Add center-specific watermark
        watermarked_paper = WatermarkEngine.embed_watermark(
            decrypted,
            req.center_id,
            req.session_token
        )

        # Store successful unlock in audit logs
        db.log_audit(
            "PAPER_UNLOCKED",
            {
                "center_id": req.center_id
            }
        )

        return {
            "paper_payload": watermarked_paper
        }

    except Exception as e:

        # Store failed unlock attempt
        db.log_audit(
            "UNLOCK_FAILED",
            {
                "center_id": req.center_id,
                "error": str(e)
            }
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Failed to reconstruct key or decrypt payload. "
                "Shares may be invalid."
            )
        )


# ---------------------------------------------------------
# Trace Watermark
# ---------------------------------------------------------

@app.post("/api/v1/watermark/trace")
async def trace_watermark(req: TraceRequest):

    metadata = WatermarkEngine.extract_watermark(
        req.watermarked_payload
    )

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail="No watermark found in payload"
        )

    return {
        "metadata": metadata
    }

@app.get("/api/v1/paper/fetch_encrypted")
async def fetch_encrypted():
    if not EXAM_STATE.get("encrypted_paper"):
        raise HTTPException(status_code=404, detail="No paper encrypted yet")
    return {
        "encrypted_paper": base64.b64encode(EXAM_STATE["encrypted_paper"]).decode('utf-8'),
        "threshold_k": EXAM_STATE["threshold_k"],
        "exam_start_time": EXAM_STATE["exam_start_time"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
