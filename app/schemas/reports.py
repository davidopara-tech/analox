from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ReportFormat = Literal["json", "markdown"]


class ReportCreate(BaseModel):
    format: ReportFormat
    generated_by: UUID


class ReportRead(BaseModel):
    report_id: UUID
    format: ReportFormat
    content: str


class ReportListRead(BaseModel):
    id: UUID
    format: str
    created_at: datetime
