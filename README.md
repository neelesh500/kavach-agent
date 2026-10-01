# Kavach Security Agent

Kavach is a professional-grade browser extension and local backend system designed to ensure the secure generation, encryption, and decryption of exam papers. It employs advanced cryptography techniques, including Shamir's Secret Sharing, and robust system architectures to create a tamper-proof and double-gated enforcement framework.

## Project Structure
- **Backend (`api_server.py`)**: A FastAPI-based backend that handles mock dataset initialization, handles API routes for paper generation, and uses advanced cryptographic features.
- **Frontend (`kavach-extension`)**: A fast, minimal HTML/CSS/JS Google Chrome browser extension. It communicates with the backend, securely renders Decrypted papers, handles Shamir shares, and features a glowing-effect dark UI.
- **Mock DB (`database_mock.py`)**: An SQLite-based mock database initialized with dummy data to emulate in-memory operation required for the project schema.
- **Security Logic (`crypto_core.py`, `similarity_guard.py`, `watermark_engine.py`)**: Core algorithmic and data-loss prevention modules enforcing Shamir secret-splitting, AI-duplicate filtering, and embedded watermarking.

## Features
- **Secure Encrypted Papers**: Generates questions efficiently via SQLite and encrypts them using AES-GCM and Shamir's Secret Sharing (threshold-based keys).
- **Double Gate Enforcement**: Ensures exams cannot be decrypted securely without strict temporal limits (start-time locks).
- **Chrome Extension UI**: A user-friendly, aesthetic popup interface that enables easy submission, generation, extraction, and traceability without needing to operate a command line.
- **Tamper Evidence**: Tracable payloads directly identify leaks with embedded watermarks.

## How to Run

1. **Start the Backend Server**:
   Ensure you have Python installed with the necessary dependencies. You can install missing dependencies in a virtual environment (`venv`) using `pip install -r requirements.txt` (if present) or manually install `fastapi uvicorn cryptography scikit-learn pydantic`.
   ```bash
   .\venv\Scripts\python api_server.py
   ```
   The backend will start running locally at `http://0.0.0.0:8000`.

2. **Load the Chrome Extension**:
   - Open Google Chrome and navigate to `chrome://extensions/`.
   - Turn on **Developer mode** in the top right.
   - Click on **Load unpacked**.
   - Select the `kavach-extension` directory inside the project folder.

3. **Usage**:
   - Open the extension popup from your browser toolbar.
   - Verify that the connection indicator on the top says **Connected** (pulsing green dot).
   - Use the different tabs to **Generate & Encrypt** exams, collect Shamir string shares, and try to **Unlock/Decrypt** in simulated centers!

## Architecture Security
- The master decryption key is never written directly to the database or plaintext logs; it's split logically using Lagrangian polynomials.
- Trace payloads require direct symmetric hashes matching inside the embedded schema.

