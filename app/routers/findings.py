from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import (
    Candidate,
    Finding,
    FindingStatus,
    ResearchProject,
    User,
)
from app.schemas.findings import FindingCreate, FindingRead, FindingUpdate

router = APIRouter(tags=["findings"])


async def _finding_read(session: AsyncSession, finding_id: UUID) -> dict:
    row = (
        await session.execute(
            select(Finding, User.name, Candidate.name)
            .join(User, User.id == Finding.author_id)
            .outerjoin(Candidate, Candidate.id == Finding.candidate_id)
            .where(Finding.id == finding_id)
        )
    ).one()
    finding, author_name, candidate_name = row
    return {
        "id": finding.id,
        "project_id": finding.project_id,
        "candidate_id": finding.candidate_id,
        "author_id": finding.author_id,
        "conclusion": finding.conclusion,
        "status": finding.status,
        "created_at": finding.created_at,
        "author_name": author_name,
        "candidate_name": candidate_name,
    }


@router.post(
    "/projects/{project_id}/findings",
    response_model=FindingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_finding(
    project_id: UUID,
    payload: FindingCreate,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if await session.get(User, payload.author_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    if payload.candidate_id is not None and await session.get(Candidate, payload.candidate_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    finding = Finding(
        project_id=project_id,
        candidate_id=payload.candidate_id,
        author_id=payload.author_id,
        conclusion=payload.conclusion,
        status=FindingStatus.DRAFT,
    )
    session.add(finding)
    await session.commit()
    await session.refresh(finding)
    return await _finding_read(session, finding.id)


@router.get(
    "/projects/{project_id}/findings",
    response_model=list[FindingRead],
)
async def list_project_findings(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    rows = (
        await session.execute(
            select(Finding, User.name, Candidate.name)
            .join(User, User.id == Finding.author_id)
            .outerjoin(Candidate, Candidate.id == Finding.candidate_id)
            .where(Finding.project_id == project_id)
            .order_by(Finding.created_at, Finding.id)
        )
    ).all()
    return [
        {
            "id": finding.id,
            "project_id": finding.project_id,
            "candidate_id": finding.candidate_id,
            "author_id": finding.author_id,
            "conclusion": finding.conclusion,
            "status": finding.status,
            "created_at": finding.created_at,
            "author_name": author_name,
            "candidate_name": candidate_name,
        }
        for finding, author_name, candidate_name in rows
    ]


@router.patch("/findings/{finding_id}", response_model=FindingRead)
async def update_finding(
    finding_id: UUID,
    payload: FindingUpdate,
    session: AsyncSession = Depends(get_session),
):
    finding = await session.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    if finding.status != FindingStatus.DRAFT or payload.status != FindingStatus.REVIEWED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The only allowed status transition is draft to reviewed",
        )

    if payload.conclusion is not None:
        finding.conclusion = payload.conclusion
    finding.status = FindingStatus.REVIEWED
    await session.commit()
    await session.refresh(finding)
    return await _finding_read(session, finding.id)
