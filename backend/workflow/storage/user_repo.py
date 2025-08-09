import os

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, ReturnDocument

from workflow.schema.user import User

class UserRepo:
    """
    Lightweight async CRUD gateway for User documents.

    Usage:
        repo = UserRepo()
        await repo.ensure_indexes()                # setup indexes
        user = await repo.create()                 # new user
        await repo.update_sandbox(user.id, "dx‑1234")  # set sandbox id
        fetched = await repo.load(user.id)         # round‑trip
    """

    def __init__(
        self,
        mongo_uri: str = os.getenv("MONGODB_DATASOURCE_URL", "mongodb://localhost:27017"),
        db_name: str = "job_db",
        col_name: str = "users",
    ):
        self.client = AsyncIOMotorClient(mongo_uri, uuidRepresentation="standard")
        self.db = self.client[db_name]
        self.col = self.db[col_name]

    async def ensure_indexes(self):
        """Create indexes - call this once during app startup"""
        await self.col.create_index([("id", ASCENDING)], unique=True)
        await self.col.create_index("sandbox_id", sparse=True)

    # -------- CRUD --------
    async def gen_user(self, user_id: str) -> User:
        """Fetch user by id or raise FileNotFoundError."""
        doc = await self.col.find_one({"id": user_id})
        
        if not doc:
            user = User(id=user_id, sandbox_id=None)
            await self.col.insert_one(user.model_dump())
        else:
            user = User.model_validate(doc)
        return user


    async def update_sandbox(self, user_id: str, sandbox_id: str) -> User:
        """
        Atomically set / replace sandbox_id, returning the updated doc.
        """
        updated = await self.col.find_one_and_update(
            {"id": user_id},
            {"$set": {"sandbox_id": sandbox_id}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise FileNotFoundError(f"User with id {user_id} not found")
        return User.model_validate(updated)


    async def close(self):
        """Close the MongoDB connection"""
        self.client.close()