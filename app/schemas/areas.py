from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AreaCreate(BaseModel):
    name: str
    description: str | None = None


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str | None


class AreaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
