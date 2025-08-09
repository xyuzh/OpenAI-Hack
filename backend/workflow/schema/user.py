from pydantic import BaseModel

class User(BaseModel):
    id: str
    sandbox_id: str | None = None 