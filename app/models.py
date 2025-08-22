from pydantic import BaseModel, Field
from typing import Optional

class ProgramResult(BaseModel):
    title: str = Field(...)
    university: str = Field(...)
    city: Optional[str] = None
    level: Optional[str] = None
    min_score: Optional[int] = None
    dorm: Optional[bool] = None
    url: Optional[str] = None
