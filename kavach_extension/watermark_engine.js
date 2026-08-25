class KavachWatermark {
    static uuidv4() {
        return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }

    static embedWatermark(textPayload, centerId, sessionToken) {
        const metadata = {
            center_id: centerId,
            timestamp: new Date().toISOString(),
            session_token: sessionToken,
            trace_id: this.uuidv4()
        };

        const metaJson = JSON.stringify(metadata);
        const metaB64 = btoa(metaJson);

        let zwspString = "";
        for (let i = 0; i < metaB64.length; i++) {
            const charCode = metaB64.charCodeAt(i);
            const binary = charCode.toString(2).padStart(8, '0');
            for (let bit of binary) {
                if (bit === '0') {
                    zwspString += '\u200b';
                } else {
                    zwspString += '\u200c';
                }
            }
        }

        return textPayload + zwspString;
    }
}
