import os
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticCollection
from pymongo import ReturnDocument, ASCENDING

from workflow.schema.job_state import JobState
from workflow.core.message import Message


class JobStateRepo:
    def __init__(
        self,
        mongo_uri: str = os.getenv("MONGODB_DATASOURCE_URL", "mongodb://localhost:27017"),
        db_name: str = "job_db",
        col_name: str = "job_states",
    ):
        self.client = AsyncIOMotorClient(mongo_uri, uuidRepresentation="standard")
        self.db = self.client[db_name]
        self.col: AgnosticCollection = self.db[col_name]

    async def ensure_indexes(self):
        """Create indexes - call this once during app startup"""
        await self.col.create_index([("id", ASCENDING)], unique=True)

    # ---------- CRUD ----------
    async def save(self, job: JobState) -> None:
        """Insert or replace an entire JobState document."""
        job_data = job.model_dump()
        await self.col.replace_one({"id": job.id}, job_data, upsert=True)

    async def gen_job_state(self, job_id: str) -> JobState:
        doc = await self.col.find_one({"id": job_id})
        if not doc:
            raise FileNotFoundError(f"Job state with id {job_id} not found")
        return JobState.model_validate(doc)

    # ---------- partial updates ----------
    async def add_message(self, job_id: str, message: Message) -> JobState:
        """Push a single Message to the messages array and return the updated doc."""
        updated = await self.col.find_one_and_update(
            {"id": job_id},
            {"$push": {"messages": message.model_dump()}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise FileNotFoundError(f"Job state with id {job_id} not found")
        return JobState.model_validate(updated)

    async def update_status(self, job_id: str, new_state: str) -> None:
        await self.col.update_one({"id": job_id}, {"$set": {"state": new_state}})

    async def close(self):
        """Close the client connection"""
        self.client.close()