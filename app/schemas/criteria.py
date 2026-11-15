from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CriterionCreate(BaseModel):
    name: str
    description: str | None = None
    unit: str | None = None


class CriterionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    area_id: UUID
    name: str
    description: str | None
    unit: str | None


class CriterionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    unit: str | None = None
