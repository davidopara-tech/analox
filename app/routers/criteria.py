from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import ResearchArea, ResearchCriterion
from app.schemas.criteria import CriterionCreate, CriterionRead

router = APIRouter(prefix="/areas/{area_id}/criteria", tags=["research criteria"])


@router.post("", response_model=CriterionRead, status_code=status.HTTP_201_CREATED)
async def create_criterion(
    area_id: UUID,
    payload: CriterionCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchArea, area_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research area not found")

    criterion = ResearchCriterion(area_id=area_id, **payload.model_dump())
    session.add(criterion)
    await session.commit()
    await session.refresh(criterion)
    return criterion


@router.get("", response_model=list[CriterionRead])
async def list_criteria(area_id: UUID, session: AsyncSession = Depends(get_session)):
    if await session.get(ResearchArea, area_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research area not found")
    result = await session.scalars(
        select(ResearchCriterion)
        .where(ResearchCriterion.area_id == area_id)
        .order_by(ResearchCriterion.id)
    )
    return result.all()
