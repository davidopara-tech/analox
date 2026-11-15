from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import Candidate, ResearchProject
from app.schemas.candidates import CandidateCreate, CandidateRead

project_candidates_router = APIRouter(
    prefix="/projects/{project_id}/candidates",
    tags=["candidates"],
)
candidates_router = APIRouter(prefix="/candidates", tags=["candidates"])


@project_candidates_router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    project_id: UUID,
    payload: CandidateCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    candidate = Candidate(project_id=project_id, **payload.model_dump())
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate


@candidates_router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(candidate_id: UUID, session: AsyncSession = Depends(get_session)):
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@project_candidates_router.get("", response_model=list[CandidateRead])
async def list_candidates(project_id: UUID, session: AsyncSession = Depends(get_session)):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await session.scalars(
        select(Candidate)
        .where(Candidate.project_id == project_id)
        .order_by(Candidate.created_at, Candidate.id)
    )
    return result.all()
