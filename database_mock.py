import sqlite3
import json
import os
from typing import Dict, List
from datetime import datetime

class DatabaseMock:
    def __init__(self, filepath="kavach.db"):
        self.filepath = filepath
        self._init_db()
    
    def _get_connection(self):
        # We use check_same_thread=False because FastAPI might share this across threads
        conn = sqlite3.connect(self.filepath, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Create questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            ''')
            
            # Create audit_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL
                )
            ''')
            conn.commit()
            
    def add_question(self, text: str, metadata: dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO questions (text, metadata) VALUES (?, ?)", 
                (text, json.dumps(metadata))
            )
            conn.commit()
        
    def get_questions(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions")
            rows = cursor.fetchall()
            return [{"id": row["id"], "text": row["text"], "metadata": json.loads(row["metadata"])} for row in rows]
            
    def get_random_questions(self, limit: int) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [{"id": row["id"], "text": row["text"], "metadata": json.loads(row["metadata"])} for row in rows]

    def log_audit(self, event_type: str, details: dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (timestamp, event_type, details) VALUES (?, ?, ?)",
                (datetime.utcnow().isoformat(), event_type, json.dumps(details))
            )
            conn.commit()
        
    def clear(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions")
            cursor.execute("DELETE FROM audit_logs")
            conn.commit()
