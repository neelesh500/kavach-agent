import os
from datetime import datetime, timezone
from typing import Dict, List

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
try:
    from mongomock_motor import AsyncMongoMockClient
except ImportError:
    AsyncMongoMockClient = None

load_dotenv()


class DatabaseMongoDB:
    def __init__(self):
        mongo_uri = os.getenv("MONGODB_URI")
        database_name = os.getenv("MONGODB_DATABASE")

        if not mongo_uri:
            raise ValueError("MONGODB_URI is not configured")

        if not database_name:
            raise ValueError("MONGODB_DATABASE is not configured")

        if mongo_uri.startswith("mock://"):
            if AsyncMongoMockClient is None:
                raise ValueError("mongomock_motor is required for mock:// URIs")
            self.client = AsyncMongoMockClient()
        else:
            self.client = AsyncMongoClient(mongo_uri)
            
        self.db = self.client[database_name]
        self.questions = self.db["questions"]
        self.audit_logs = self.db["audit_logs"]

    async def _seed_mock_if_needed(self):
        # Auto-seed mock db with 180 questions if empty (for ZEEA testing)
        count = await self.questions.count_documents({})
        if count == 0 and os.path.exists("zeea_mock_db.json"):
            import json
            with open("zeea_mock_db.json", "r") as f:
                mock_data = json.load(f)
                await self.questions.insert_many(mock_data)

    async def check_connection(self):
        await self.client.admin.command("ping")
        print("MongoDB connected successfully")

    async def add_question(self, text: str, metadata: dict):
        result = await self.questions.insert_one({
            "text": text,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc)
        })

        return str(result.inserted_id)

    async def get_questions(self) -> List[Dict]:
        await self._seed_mock_if_needed()
        cursor = self.questions.find({})

        questions = []

        async for question in cursor:
            questions.append({
                "id": str(question["_id"]),
                "text": question["text"],
                "metadata": question.get("metadata", {})
            })

        return questions

    async def get_random_questions(self, limit: int) -> List[Dict]:
        pipeline = [
            {"$sample": {"size": limit}}
        ]

        cursor = self.questions.aggregate(pipeline)

        questions = []

        async for question in cursor:
            questions.append({
                "id": str(question["_id"]),
                "text": question["text"],
                "metadata": question.get("metadata", {})
            })

        return questions

    async def log_audit(self, event_type: str, details: dict):
        await self.audit_logs.insert_one({
            "timestamp": datetime.now(timezone.utc),
            "event_type": event_type,
            "details": details
        })

    async def clear(self):
        await self.questions.delete_many({})
        await self.audit_logs.delete_many({})

    async def close(self):
        await self.client.close()