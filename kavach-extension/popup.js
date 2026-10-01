const API_BASE = "http://localhost:8000/api/v1";

document.addEventListener("DOMContentLoaded", () => {
    // Check Backend Connection automatically every 2 seconds
    checkBackendConnection();
    setInterval(checkBackendConnection, 2000);

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
                    <button id="downloadSharesBtn" class="action-btn" style="background: var(--accent-color); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px;">
                        ⬇️ Download Paper & Shares (Admin View)
                    </button>
                </div>
            `;
            showAlert('Paper generated and encrypted', 'success');

            // Setup actual download action
            document.getElementById('downloadSharesBtn').addEventListener('click', (e) => {
                e.preventDefault();

                let shareLines = encryptData.shares.map((s, i) => `<b>Share ${i + 1}:</b> <code>[X: ${s[0]}, Y: ${s[1]}]</code>`).join('<br>');

                // Format the paper raw text into a professional layout!
                let formattedPaper = paperText
                    .replace(/======(.*?)======/g, '<h2 class="paper-header">$1</h2>')
                    .replace(/--- SECTION: (.*?) ---/g, '<h3 class="section-title">$1</h3>')
                    .replace(/(Q\d+\..*?)\n/g, '<div class="question"><b>$1</b></div>')
                    .replace(/   ([A-D]\) .*?)(?=\n|$)/g, '<div class="option">$1</div>');

                const htmlContent = `
                    <html>
                        <head>
                            <title>Kavach_Secure_Paper_${Date.now()}</title>
                            <style>
                                body { font-family: 'Times New Roman', serif; background: #fff; color: #000; padding: 40px; line-height: 1.6; max-width: 900px; margin: 0 auto; }
                                .container { border: 2px solid #222; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
                                
                                /* Ticket Styling */
                                .ticket-section { border-bottom: 2px dashed #666; padding-bottom: 30px; margin-bottom: 30px; font-family: 'Arial', sans-serif; }
                                .ticket-header { text-align: center; color: #1e3a8a; border-bottom: 1px solid #1e3a8a; padding-bottom: 15px; text-transform: uppercase; letter-spacing: 2px; }
                                .meta-info { display: flex; justify-content: space-between; margin-top: 20px; font-size: 14px; background: #f8fafc; padding: 15px; border-left: 4px solid #1e3a8a; }
                                .warning { margin-top: 20px; color: #b91c1c; font-weight: bold; background: #fee2e2; padding: 10px; text-align: center; border-radius: 4px; }
                                .shares-container { margin-top: 20px; background: #f1f5f9; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 13px; line-height: 1.8; word-break: break-all; }
                                
                                /* Paper Styling */
                                .paper-section { position: relative; }
                                .paper-header { text-align: center; text-transform: uppercase; font-size: 22px; margin-bottom: 30px; border-bottom: 2px solid #000; padding-bottom: 10px; }
                                .section-title { font-size: 18px; text-decoration: underline; margin-top: 30px; margin-bottom: 15px; }
                                .question { font-size: 15px; margin-top: 20px; text-align: justify; }
                                .option { margin-left: 20px; font-size: 14px; margin-top: 5px; }
                                
                                .footer { text-align: center; margin-top: 40px; font-size: 12px; color: #666; border-top: 1px solid #ccc; padding-top: 15px; font-family: Arial, sans-serif; }
                                
                                @media print {
                                    body { padding: 0; box-shadow: none; }
                                    .container { border: none; padding: 0; box-shadow: none; }
                                }
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <!-- Secure Ticket Header -->
                                <div class="ticket-section">
                                    <h2 class="ticket-header">🔒 KAVACH SECURE EXAM TICKET</h2>
                                    <div class="meta-info">
                                        <div><b>Date Generated:</b> ${new Date().toLocaleString()}<br><b>Total Shares:</b> 5</div>
                                        <div><b>Threshold (K):</b> 3 (Minimum required to unlock)<br><b>System:</b> Kavach Enforcer</div>
                                    </div>
                                    <div class="warning">
                                        ⚠ CONFIDENTIAL: Keep the following share keys strictly confidential! Distribute them across distinct examination centers.
                                    </div>
                                    <div class="shares-container">
                                        <h3>SHARE KEYS</h3>
                                        ${shareLines}
                                    </div>
                                </div>

                                <!-- Actual Generated Paper Preview -->
                                <div class="paper-section">
                                    <div style="text-align: center; font-family: Arial; color: #666; font-size: 11px; letter-spacing: 2px; margin-bottom: 20px;">
                                        --- ADMIN / JUDGE PREVIEW BELOW ---
                                    </div>
                                    ${formattedPaper}
                                </div>
                                
                                <div class="footer">
                                    Document securely generated by Project Kavach.<br>
                                    Only valid for preview configuration.
                                </div>
                            </div>
                        </body>
                    </html>
                `;

                // Open in a new tab to reliably trigger PDF print dialog from the extension
                let printWindow = window.open('', '_blank');
                if (printWindow) {
                    printWindow.document.write(htmlContent);
                    printWindow.document.close();
                    setTimeout(() => {
                        printWindow.print();
                    }, 500);
                } else {
                    showAlert('Window blocked! Please allow popups.', 'error');
                }
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

        let printWindow = window.open('', '_blank');
        if (printWindow) {
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
        } else {
            showAlert('Window blocked! Please allow popups.', 'error');
        }
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
        const res = await fetch("http://localhost:8000/openapi.json");
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
