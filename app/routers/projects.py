from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import ResearchProject, User, Workspace
from app.schemas.projects import ProjectCreate, ProjectRead

workspace_projects_router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects",
    tags=["projects"],
)
projects_router = APIRouter(prefix="/projects", tags=["projects"])


@workspace_projects_router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    workspace_id: UUID,
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Workspace, workspace_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if await session.get(User, payload.created_by) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    project = ResearchProject(workspace_id=workspace_id, **payload.model_dump())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@projects_router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, session: AsyncSession = Depends(get_session)):
    project = await session.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@workspace_projects_router.get("", response_model=list[ProjectRead])
async def list_workspace_projects(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Workspace, workspace_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    result = await session.scalars(
        select(ResearchProject)
        .where(ResearchProject.workspace_id == workspace_id)
        .order_by(ResearchProject.created_at, ResearchProject.id)
    )
    return result.all()
