from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analox import FindingStatus


class FindingCreate(BaseModel):
    candidate_id: UUID | None = None
    author_id: UUID
    conclusion: str


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    candidate_id: UUID | None
    author_id: UUID
    conclusion: str
    status: FindingStatus
    created_at: datetime
    author_name: str
    candidate_name: str | None


class FindingUpdate(BaseModel):
    status: FindingStatus
    conclusion: str | None = None
