from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analox import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str
    created_by: UUID


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_by: UUID
    created_at: datetime


class WorkspaceUpdate(BaseModel):
    name: str | None = None


class WorkspaceMemberCreate(BaseModel):
    user_id: UUID
    role: WorkspaceRole


class WorkspaceMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    joined_at: datetime


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole | None = None
