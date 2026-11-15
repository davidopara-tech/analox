from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import ProjectAssignment, ResearchProject, User
from app.schemas.assignments import AssignmentCreate, AssignmentRead

router = APIRouter(prefix="/projects/{project_id}/assignments", tags=["assignments"])


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    project_id: UUID,
    payload: AssignmentCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if await session.get(User, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    if await session.get(User, payload.assigned_by) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigning user not found")

    assignment = ProjectAssignment(project_id=project_id, **payload.model_dump())
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment


@router.get("", response_model=list[AssignmentRead])
async def list_assignments(project_id: UUID, session: AsyncSession = Depends(get_session)):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await session.scalars(
        select(ProjectAssignment)
        .where(ProjectAssignment.project_id == project_id)
        .order_by(ProjectAssignment.created_at, ProjectAssignment.id)
    )
    return result.all()
