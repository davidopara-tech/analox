from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analox import PlanetTarget, ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    target: PlanetTarget
    created_by: UUID


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    target: PlanetTarget
    status: ProjectStatus
    is_sample: bool
    created_by: UUID
    created_at: datetime


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target: PlanetTarget | None = None
    status: ProjectStatus | None = None
    is_sample: bool | None = None
