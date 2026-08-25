class KavachCrypto {
    static PRIME = BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F"); // 2^256 - 2^32 - 977 (secp256k1 prime)

    static modInverse(a, m) {
        let m0 = m;
        let y = 0n;
        let x = 1n;

        if (m === 1n) return 0n;

        // Extended Euclidean algorithm
        while (a > 1n) {
            let q = a / m;
            let t = m;
            m = a % m;
            a = t;
            t = y;
            y = x - q * y;
            x = t;
        }

        if (x < 0n) x += m0;
        return x;
    }

    static reconstructSecret(shares, k) {
        if (shares.length < k) {
            throw new Error("Not enough shares to reconstruct");
        }

        shares = shares.slice(0, k);
        let secret = 0n;

        for (let i = 0; i < k; i++) {
            let x_i = BigInt(shares[i][0]);
            let y_i = BigInt(shares[i][1]);

            let numerator = 1n;
            let denominator = 1n;

            for (let j = 0; j < k; j++) {
                if (i !== j) {
                    let x_j = BigInt(shares[j][0]);

                    numerator = (numerator * (-x_j)) % this.PRIME;
                    denominator = (denominator * (x_i - x_j)) % this.PRIME;
                }
            }

            // Ensure negative numbers modulo prime are correctly mapped to positive
            if (numerator < 0n) {
                numerator = (numerator % this.PRIME + this.PRIME) % this.PRIME;
            }
            if (denominator < 0n) {
                denominator = (denominator % this.PRIME + this.PRIME) % this.PRIME;
            }

            let modInv = this.modInverse(denominator, this.PRIME);
            let lagrangePoly = (y_i * numerator * modInv) % this.PRIME;
            secret = (this.PRIME + secret + lagrangePoly) % this.PRIME;
        }

        return secret;
    }

    static async decryptPayload(secretBigInt, ciphertextWithNonceBase64) {
        let hex = secretBigInt.toString(16);
        while (hex.length < 64) hex = '0' + hex; // pad to 32 bytes (64 hex chars)

        let keyBytes = new Uint8Array(32);
        for (let i = 0; i < 32; i++) {
            keyBytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
        }

        const key = await window.crypto.subtle.importKey(
            "raw",
            keyBytes,
            { name: "AES-GCM" },
            false,
            ["decrypt"]
        );

        // ciphertext base64 decode
        const rawString = atob(ciphertextWithNonceBase64);
        const data = new Uint8Array(rawString.length);
        for (let i = 0; i < rawString.length; i++) {
            data[i] = rawString.charCodeAt(i);
        }

        const nonce = data.slice(0, 12);
        const ciphertext = data.slice(12);

        try {
            const decryptedBuffer = await window.crypto.subtle.decrypt(
                { name: "AES-GCM", iv: nonce },
                key,
                ciphertext
            );
            return new TextDecoder().decode(decryptedBuffer);
        } catch (e) {
            throw new Error("Decryption failed. Invalid shares or modified ciphertext.");
        }
    }
}
