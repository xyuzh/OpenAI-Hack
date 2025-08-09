from pydantic import BaseModel
from typing import Optional

class BashOps(BaseModel):
    cmd: str
    env: Optional[dict[str, str]] = None
    timeout: Optional[int] = None


