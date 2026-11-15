from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import ResearchArea, ResearchProject
from app.schemas.areas import AreaCreate, AreaRead

router = APIRouter(prefix="/projects/{project_id}/areas", tags=["research areas"])


@router.post("", response_model=AreaRead, status_code=status.HTTP_201_CREATED)
async def create_area(
    project_id: UUID,
    payload: AreaCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    area = ResearchArea(project_id=project_id, **payload.model_dump())
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area


@router.get("", response_model=list[AreaRead])
async def list_areas(project_id: UUID, session: AsyncSession = Depends(get_session)):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await session.scalars(
        select(ResearchArea)
        .where(ResearchArea.project_id == project_id)
        .order_by(ResearchArea.id)
    )
    return result.all()
