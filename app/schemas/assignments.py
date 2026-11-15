from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analox import AssignmentStatus


class AssignmentCreate(BaseModel):
    user_id: UUID
    task: str
    assigned_by: UUID


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    task: str
    status: AssignmentStatus
    assigned_by: UUID
    created_at: datetime


class AssignmentUpdate(BaseModel):
    user_id: UUID | None = None
    task: str | None = None
    status: AssignmentStatus | None = None
    assigned_by: UUID | None = None
