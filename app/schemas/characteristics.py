from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CharacteristicCreate(BaseModel):
    criterion_id: UUID
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    source_id: UUID
    notes: str | None = None
    is_mock: bool


class CharacteristicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_id: UUID
    criterion_id: UUID
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    source_id: UUID
    is_mock: bool
    notes: str | None


class CharacteristicUpdate(BaseModel):
    criterion_id: UUID | None = None
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    source_id: UUID | None = None
    notes: str | None = None
    is_mock: bool | None = None
