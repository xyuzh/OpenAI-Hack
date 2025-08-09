from pydantic import BaseModel, Field
from typing import Annotated


class JobPlan(BaseModel):
    name: Annotated[str, Field(description='Job name in snake_case')]

    plan: Annotated[
        str,
        Field(description="""An actionable plan for AI agent"""),
    ]
