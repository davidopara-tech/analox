from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CandidateCreate(BaseModel):
    name: str
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    region: str | None = None
    country: str | None = None


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str | None
    latitude: float | None
    longitude: float | None
    region: str | None
    country: str | None
    is_mock: bool
    created_at: datetime


class CandidateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    region: str | None = None
    country: str | None = None
    is_mock: bool | None = None
