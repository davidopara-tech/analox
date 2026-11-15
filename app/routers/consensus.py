import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.services.consensus import ConsensusError, _kind, compute_consensus

router = APIRouter(prefix="/projects/{project_id}", tags=["consensus"])


class WeightsBody(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)


@router.post("/consensus")
async def post_consensus(
    project_id: uuid.UUID,
    body: WeightsBody | None = None,
    session: AsyncSession = Depends(get_session),
):
    weights = body.weights if body and body.weights else None
    try:
        return await compute_consensus(session, project_id, weights)
    except ConsensusError as exc:
        raise HTTPException(status_code=_kind(str(exc)), detail=str(exc)) from exc