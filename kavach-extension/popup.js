const API_BASE = "http://127.0.0.1:8000/api/v1";

document.addEventListener("DOMContentLoaded", () => {
    // Check Backend Connection
    checkBackendConnection();

    // Tab Navigation
    const tabs = document.querySelectorAll('.tab-btn');
    const views = document.querySelectorAll('.view-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class
            tabs.forEach(t => t.classList.remove('active'));
            views.forEach(v => v.classList.remove('active', 'hidden'));

            // Add active class to clicked
            tab.classList.add('active');

            // Show corresponding view
            const targetId = tab.getAttribute('data-target');
            views.forEach(v => {
                if (v.id === targetId) {
                    v.classList.add('active');
                } else {
                    v.classList.add('hidden');
                }
            });
        });
    });

    // Submitting a Question
    document.getElementById('submitBtn').addEventListener('click', async () => {
        const text = document.getElementById('questionInput').value.trim();
        const metaText = document.getElementById('metadataInput').value.trim();
        const btn = document.getElementById('submitBtn');

        if (!text) return showAlert('Question text is required', 'error');

        let metadata = {};
        if (metaText) {
            try {
                metadata = JSON.parse(metaText);
            } catch (e) {
                return showAlert('Invalid JSON in metadata', 'error');
            }
        }

        setLoading(btn, true);
        try {
            const res = await fetch(`${API_BASE}/questions/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_text: text,
                    metadata: metadata
                })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || 'Submit failed');

            document.getElementById('questionInput').value = '';
            showAlert('Question submitted successfully!', 'success');
        } catch (err) {
            showAlert(err.message, 'error');
        } finally {
            setLoading(btn, false, 'Submit Question');
        }
    });

    // Generating Paper
    document.getElementById('generateBtn').addEventListener('click', async () => {
        const num = document.getElementById('numQuestionsInput').value;
        const btn = document.getElementById('generateBtn');

        setLoading(btn, true);
        try {
            // 1. Generate Paper
            let res = await fetch(`${API_BASE}/paper/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ num_questions: parseInt(num) || 5 })
            });
            let data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to generate');

            const paperText = data.paper_text;

            // 2. Encrypt Paper
            const encryptRes = await fetch(`${API_BASE}/paper/encrypt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_text: paperText,
                    exam_start_time: (Date.now() / 1000) - 3600, // 1 hr in past so we can immediately decrypt!
                    threshold_k: 3,
                    total_shares: 5
                })
            });
            const encryptData = await encryptRes.json();
            if (!encryptRes.ok) throw new Error(encryptData.detail || 'Failed to encrypt');

            const resultBox = document.getElementById('paperResultBox');
            resultBox.classList.remove('hidden');
            resultBox.innerHTML = `
                <h4>Success! Encrypted Paper Created</h4>
                <p class="small-info">Generated ${encryptData.shares.length} shares. Paper is masked.</p>
                <div style="margin-top: 12px;">
                    <button id="downloadSharesBtn" style="background: var(--accent-color); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px;">
                        ⬇️ Download Paper & Shares
                    </button>
                </div>
            `;
            showAlert('Paper generated and encrypted', 'success');

            // Setup actual download action
            document.getElementById('downloadSharesBtn').addEventListener('click', (e) => {
                e.preventDefault();

                let shareLines = encryptData.shares.map((s, i) => `Share ${i + 1}:  [X: ${s[0]}, Y: ${s[1]}]`).join('\n');

                const readableText = `================================================
           KAVACH SECURE EXAM TICKET
================================================

Date Generated : ${new Date().toLocaleString()}
Threshold (K)  : 3 (Minimum required to unlock)
Total Shares   : 5

Keep the following share keys strictly confidential! 
Distribute them among distinct examination centers.

------------------------------------------------
SHARE KEYS:
------------------------------------------------
${shareLines}

================================================
NOTE: This is an auto-generated secure document.
================================================`;

                const blob = new Blob([readableText], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Kavach_Secure_Paper_${Date.now()}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showAlert('Text document downloaded!', 'success');
            });

        } catch (err) {
            showAlert(err.message, 'error');
        } finally {
            setLoading(btn, false, 'Generate & Encrypt');
        }
    });

    // Decrypt Paper
    let decryptedPaperStore = "";
    document.getElementById('decryptBtn').addEventListener('click', async () => {
        const sharesText = document.getElementById('decryptSharesInput').value.trim();
        const centerId = document.getElementById('decryptCenterInput').value.trim();
        const btn = document.getElementById('decryptBtn');
        const resultBox = document.getElementById('decryptResultBox');
        const resultText = document.getElementById('decryptResultText');

        if (!sharesText || !centerId) return showAlert('Missing fields', 'error');

        let shares;
        try {
            shares = JSON.parse(sharesText);
        } catch (e) {
            return showAlert('Invalid JSON shares', 'error');
        }

        setLoading(btn, true);
        resultBox.classList.add('hidden');
        try {
            const res = await fetch(`${API_BASE}/paper/unlock`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shares: shares,
                    center_id: centerId,
                    session_token: 'agent_session_' + Date.now()
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Decryption failed');

            decryptedPaperStore = data.paper_payload;
            resultText.textContent = decryptedPaperStore;
            resultBox.classList.remove('hidden');
            showAlert('Paper successfully decrypted by AI Enforcer!', 'success');
        } catch (err) {
            showAlert(err.message, 'error');
        } finally {
            setLoading(btn, false, 'Decrypt Encrypted Paper');
        }
    });

    // Save as PDF / Print functionality
    document.getElementById('downloadPdfBtn').addEventListener('click', () => {
        if (!decryptedPaperStore) return;

        let printWindow = window.open('', '', 'height=800,width=800');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Kavach - Official Decrypted Exam Paper</title>
                    <style>
                        body { font-family: 'Helvetica Neue', Arial, sans-serif; padding: 40px; color: #111; line-height: 1.6; }
                        h1 { text-align: center; color: #b91c1c; border-bottom: 2px solid #ccc; padding-bottom: 20px; }
                        .content { margin-top: 30px; white-space: pre-wrap; font-size: 14pt; }
                        .footer { margin-top: 50px; font-size: 10pt; color: #666; border-top: 1px solid #ccc; padding-top: 10px; text-align: center; }
                    </style>
                </head>
                <body>
                    <h1>KAVACH SECURE EXAM PAPER</h1>
                    <div class="content">${decryptedPaperStore.replace(/</g, "&lt;")}</div>
                    <div class="footer">Generated securely by Kavach Agent. Automatically watermarked for trace security.</div>
                </body>
            </html>
        `);
        printWindow.document.close();

        // Wait a small delay to ensure images/CSS are loaded before printing
        setTimeout(() => {
            printWindow.print();
        }, 250);
    });

    // Trace Watermark
    document.getElementById('traceBtn').addEventListener('click', async () => {
        const payloadText = document.getElementById('tracePayloadInput').value.trim();
        const btn = document.getElementById('traceBtn');
        const resultBox = document.getElementById('traceResultBox');
        const resultText = document.getElementById('traceResultText');

        if (!payloadText) return showAlert('Payload text required', 'error');

        setLoading(btn, true);
        resultBox.classList.add('hidden');
        try {
            const res = await fetch(`${API_BASE}/watermark/trace`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ watermarked_payload: payloadText })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || 'Trace failed');

            resultText.textContent = JSON.stringify(data.metadata, null, 2);
            resultBox.classList.remove('hidden');
            showAlert('Watermark traced successfully!', 'success');
        } catch (err) {
            showAlert(err.message, 'error');
        } finally {
            setLoading(btn, false, 'Run Trace Routine');
        }
    });
});

async function checkBackendConnection() {
    const dot = document.getElementById('backendStatus');
    const text = document.getElementById('backendStatusText');

    try {
        // Just checking if we can resolve the root API route or similar.
        // We'll just fetch the OpenAPI definition to see if it's alive.
        const res = await fetch("http://127.0.0.1:8000/openapi.json");
        if (res.ok) {
            dot.className = 'pulse-dot green';
            text.textContent = 'Connected';
        } else {
            throw new Error('Not ok');
        }
    } catch (err) {
        dot.className = 'pulse-dot red';
        text.textContent = 'Disconnected';
    }
}

function setLoading(btn, isLoading, originalText = '') {
    if (isLoading) {
        btn.disabled = true;
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <path d="M21 12a9 9 0 11-6.219-8.56"></path>
        </svg> Working...`;
    } else {
        btn.disabled = false;
        btn.innerHTML = `<span>${originalText}</span>`;
    }
}

function showAlert(message, type = 'success') {
    const container = document.getElementById('alertsContainer');
    const alert = document.createElement('div');
    alert.className = `alert ${type}`;

    const icon = type === 'success'
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

    alert.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(alert);

    setTimeout(() => {
        alert.classList.add('alert-fadeOut');
        setTimeout(() => alert.remove(), 300);
    }, 4000);
}

// Global scope for spinning svg
const style = document.createElement('style');
style.textContent = `
    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { 100% { transform: rotate(360deg); } }
`;
document.head.appendChild(style);
