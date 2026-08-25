// Tab switching
document.getElementById('tabAdmin').addEventListener('click', () => {
    document.getElementById('tabAdmin').classList.add('active');
    document.getElementById('tabCenter').classList.remove('active');
    document.getElementById('panelAdmin').classList.remove('hidden');
    document.getElementById('panelCenter').classList.add('hidden');
    hideResult();
});
document.getElementById('tabCenter').addEventListener('click', () => {
    document.getElementById('tabCenter').classList.add('active');
    document.getElementById('tabAdmin').classList.remove('active');
    document.getElementById('panelCenter').classList.remove('hidden');
    document.getElementById('panelAdmin').classList.add('hidden');
    hideResult();
});

function showResult(text, isError = false) {
    const res = document.getElementById('result');
    res.style.display = 'block';
    res.textContent = text;
    res.className = isError ? 'error-msg' : '';
}
function hideResult() {
    document.getElementById('result').style.display = 'none';
}

// 1. Admin: Generate and Encrypt Paper
document.getElementById('adminGenerateBtn').addEventListener('click', async () => {
    const apiUrl = document.getElementById('apiUrl').value;
    const numQ = parseInt(document.getElementById('numQuestions').value);
    const k = parseInt(document.getElementById('thresholdK').value);
    const n = parseInt(document.getElementById('totalShares').value);

    showResult("Generating paper...");

    try {
        // Generate plaintext paper internally
        const genRes = await fetch(`${apiUrl}/api/v1/paper/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ num_questions: numQ })
        });
        if (!genRes.ok) throw new Error("Paper generation failed on server");
        const genData = await genRes.json();

        // Encrypt the paper and create shares
        const encRes = await fetch(`${apiUrl}/api/v1/paper/encrypt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper_text: genData.paper_text,
                exam_start_time: Date.now() / 1000 - 60, // Simulate valid time (-60s ago)
                threshold_k: k,
                total_shares: n
            })
        });

        if (!encRes.ok) throw new Error("Encryption failed on server");
        const encData = await encRes.json();

        showResult(`Success!\n\nShares generated:\n${JSON.stringify(encData.shares)}\n\n(Save these to simulate Center check)`);
        document.getElementById('sharesInput').value = JSON.stringify(encData.shares.slice(0, k));
    } catch (err) {
        showResult(`Error: ${err.message}`, true);
    }
});

// 2. Center: Unlock with Shares (100% Client-Side)
document.getElementById('centerUnlockBtn').addEventListener('click', async () => {
    const apiUrl = document.getElementById('apiUrlCenter').value;
    const centerId = document.getElementById('centerId').value;
    const sharesText = document.getElementById('sharesInput').value;

    showResult("Verifying double-gate and fetching encrypted paper...");

    try {
        let shares;
        try {
            shares = JSON.parse(sharesText);
        } catch (e) {
            throw new Error("Invalid JSON format for shares");
        }

        // Fetch the encrypted paper from the backend (True zero-trust client model)
        const fetchRes = await fetch(`${apiUrl}/api/v1/paper/fetch_encrypted`);
        if (!fetchRes.ok) throw new Error("Could not fetch encrypted paper from server");
        const data = await fetchRes.json();

        const currentUnix = Date.now() / 1000;
        if (currentUnix < data.exam_start_time) {
            throw new Error("Double-Gate Check Failed: Exam strict start time not reached.");
        }

        showResult("Reconstructing Shamir's Secret locally...");
        // Reconstruct secret using BigInt in JS natively
        const secretBigInt = KavachCrypto.reconstructSecret(shares, data.threshold_k);

        showResult("Decrypting AES-GCM payload in browser...");
        const plaintext = await KavachCrypto.decryptPayload(secretBigInt, data.encrypted_paper);

        showResult("Applying embedded forensics watermark...");
        const sessionToken = "ST-" + Math.random().toString(36).substring(7);
        const watermarked = KavachWatermark.embedWatermark(plaintext, centerId, sessionToken);

        showResult(`🔓 EXAM PAPER UNLOCKED 🔓\n\n${watermarked}`);

    } catch (err) {
        showResult(`Error: ${err.message}`, true);
    }
});
