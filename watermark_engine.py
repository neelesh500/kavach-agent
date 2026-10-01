import json
import base64
import uuid
import datetime

class WatermarkEngine:
    """Provides imperceptible zero-width character steganography for anti-leak tracking"""
    
    @staticmethod
    def embed_watermark(text_payload: str, center_id: str, session_token: str) -> str:
        """Injects a traceable hidden watermark into the payload tail"""
        metadata = {
            "center_id": center_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "session_token": session_token,
            "trace_id": str(uuid.uuid4())
        }
        meta_json = json.dumps(metadata)
        meta_b64 = base64.b64encode(meta_json.encode()).decode()
        
        # Convert base64 string to zero-width binary
        zwsp_chars = []
        for char in meta_b64:
            binary = format(ord(char), '08b')
            for bit in binary:
                if bit == '0':
                    zwsp_chars.append('\u200b')
                else:
                    zwsp_chars.append('\u200c')
                    
        zwsp_string = ''.join(zwsp_chars)
        return text_payload + zwsp_string

    @staticmethod
    def extract_watermark(watermarked_payload: str) -> dict:
        """Decodes zero-width string characters back into metadata payload"""
        zwsp_chars = [c for c in watermarked_payload if c in ('\u200b', '\u200c')]
        if not zwsp_chars:
            return {}
            
        binary = ''
        for c in zwsp_chars:
            if c == '\u200b':
                binary += '0'
            elif c == '\u200c':
                binary += '1'
                
        chars = []
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
                
        meta_b64 = ''.join(chars)
        try:
            meta_json = base64.b64decode(meta_b64).decode()
            return json.loads(meta_json)
        except Exception:
            return {}
