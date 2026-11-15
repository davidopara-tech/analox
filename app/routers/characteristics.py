from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import (
    Candidate,
    CandidateCharacteristic,
    ResearchCriterion,
    Source,
)
from app.schemas.characteristics import CharacteristicCreate, CharacteristicRead

router = APIRouter(
    prefix="/candidates/{candidate_id}/characteristics",
    tags=["candidate characteristics"],
)


@router.post("", response_model=CharacteristicRead, status_code=status.HTTP_201_CREATED)
async def create_characteristic(
    candidate_id: UUID,
    payload: CharacteristicCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if await session.get(ResearchCriterion, payload.criterion_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research criterion not found")
    if await session.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    characteristic = CandidateCharacteristic(candidate_id=candidate_id, **payload.model_dump())
    session.add(characteristic)
    await session.commit()
    await session.refresh(characteristic)
    return characteristic


@router.get("", response_model=list[CharacteristicRead])
async def list_characteristics(
    candidate_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    result = await session.scalars(
        select(CandidateCharacteristic)
        .where(CandidateCharacteristic.candidate_id == candidate_id)
        .order_by(CandidateCharacteristic.id)
    )
    return result.all()
