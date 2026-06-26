from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ApplicationBase(BaseModel):
    name: str
    description: Optional[str] = None
    git_repo: str
    git_branch: str = "main"
    environment: str

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationRead(ApplicationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)