from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceCreate(BaseModel):
    title: str
    url: str | None = None
    citation: str | None = None
    retrieved_at: datetime | None = None


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    url: str | None
    citation: str | None
    retrieved_at: datetime | None
    created_at: datetime


class SourceUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    citation: str | None = None
    retrieved_at: datetime | None = None
