import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import (
    Candidate,
    CandidateCharacteristic,
    Finding,
    FindingStatus,
    Report,
    ResearchCriterion,
    ResearchProject,
    Source,
    User,
)
from app.schemas.reports import ReportCreate, ReportListRead, ReportRead
from app.services.consensus import ConsensusError, compute_consensus

router = APIRouter(tags=["reports"])

METHODOLOGY_NOTE = (
    "Similarity scores are computed at read time and do not constitute scientific confirmation."
)
SAMPLE_DATA_WARNING = (
    "> **Warning:** This report includes sample/mock data. Not verified."
)


def _render_markdown(project_name: str, payload: dict) -> str:
    lines = [f"# {project_name}", ""]
    if payload["sample_data_warning"]:
        lines.extend([SAMPLE_DATA_WARNING, ""])

    lines.extend(
        [
            "## Consensus summary",
            "",
            "| Candidate | Total | Per area |",
            "| --- | ---: | --- |",
        ]
    )
    for item in payload["consensus_summary"]:
        total = "N/A" if item["total"] is None else str(item["total"])
        areas = "; ".join(
            f"{area['area']}: {area['score'] if area['score'] is not None else 'N/A'}"
            for area in item["per_area"].values()
        )
        lines.append(f"| {item['candidate_name']} | {total} | {areas} |")
    if not payload["consensus_summary"]:
        lines.append("| No consensus results | N/A | N/A |")

    lines.extend(["", "## Findings", ""])
    if payload["findings"]:
        for finding in payload["findings"]:
            candidate = finding["candidate_name"] or "Unspecified candidate"
            lines.append(
                f"- **{candidate}** — {finding['conclusion']} "
                f"(by {finding['author_name']}; {finding['created_at']})"
            )
    else:
        lines.append("No reviewed findings.")

    lines.extend(["", "## Evidence", ""])
    if payload["evidence"]:
        for evidence in payload["evidence"]:
            value = (
                evidence["value_numeric"]
                if evidence["value_numeric"] is not None
                else evidence["value_text"]
            )
            units = f" {evidence['unit']}" if evidence["unit"] else ""
            source = evidence["source"]
            lines.append(
                f"- **{evidence['candidate_name']} — {evidence['criterion']}:** "
                f"{value}{units}; source: {source['title']} "
                f"({source['url'] or source['citation'] or 'no URL or citation'})"
            )
    else:
        lines.append("No evidence characteristics.")

    lines.extend(["", "## Methodology", "", payload["methodology_note"]])
    return "\n".join(lines)


@router.post(
    "/projects/{project_id}/reports",
    response_model=ReportRead,
    status_code=status.HTTP_200_OK,
)
async def create_report(
    project_id: UUID,
    payload: ReportCreate,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if await session.get(User, payload.generated_by) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generating user not found")

    finding_rows = (
        await session.execute(
            select(Finding, User.name, Candidate.name)
            .join(User, User.id == Finding.author_id)
            .outerjoin(Candidate, Candidate.id == Finding.candidate_id)
            .where(
                Finding.project_id == project_id,
                Finding.status == FindingStatus.REVIEWED,
            )
            .order_by(Finding.created_at, Finding.id)
        )
    ).all()
    findings = [
        {
            "candidate_id": finding.candidate_id,
            "candidate_name": candidate_name,
            "conclusion": finding.conclusion,
            "author_name": author_name,
            "created_at": finding.created_at.isoformat(),
        }
        for finding, author_name, candidate_name in finding_rows
    ]

    candidate_ids = list(
        {
            finding["candidate_id"]
            for finding in findings
            if finding["candidate_id"] is not None
        }
    )
    evidence = []
    sample_data_warning = False
    if candidate_ids:
        evidence_rows = (
            await session.execute(
                select(
                    Candidate.name,
                    ResearchCriterion.name,
                    CandidateCharacteristic.value_numeric,
                    CandidateCharacteristic.value_text,
                    CandidateCharacteristic.unit,
                    CandidateCharacteristic.is_mock,
                    Source.title,
                    Source.url,
                    Source.citation,
                )
                .join(
                    Candidate,
                    Candidate.id == CandidateCharacteristic.candidate_id,
                )
                .join(
                    ResearchCriterion,
                    ResearchCriterion.id == CandidateCharacteristic.criterion_id,
                )
                .join(Source, Source.id == CandidateCharacteristic.source_id)
                .where(CandidateCharacteristic.candidate_id.in_(candidate_ids))
                .order_by(Candidate.name, ResearchCriterion.name)
            )
        ).all()
        for (
            candidate_name,
            criterion_name,
            value_numeric,
            value_text,
            unit,
            is_mock,
            source_title,
            source_url,
            source_citation,
        ) in evidence_rows:
            sample_data_warning = sample_data_warning or is_mock
            evidence.append(
                {
                    "candidate_name": candidate_name,
                    "criterion": criterion_name,
                    "value_numeric": value_numeric,
                    "value_text": value_text,
                    "unit": unit,
                    "source": {
                        "title": source_title,
                        "url": source_url,
                        "citation": source_citation,
                    },
                }
            )

    try:
        consensus = await compute_consensus(session, project_id)
    except ConsensusError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    project_target = project.target.value
    report_payload = {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "target": project_target,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "consensus_summary": [
            {
                "candidate_name": item["candidate_name"],
                "total": item["total"],
                "per_area": item["per_area"],
            }
            for item in consensus["results"][:3]
        ],
        "findings": [
            {
                "candidate_name": finding["candidate_name"],
                "conclusion": finding["conclusion"],
                "author_name": finding["author_name"],
                "created_at": finding["created_at"],
            }
            for finding in findings
        ],
        "evidence": evidence,
        "sample_data_warning": sample_data_warning,
        "methodology_note": METHODOLOGY_NOTE,
    }

    if payload.format == "markdown":
        content = _render_markdown(project.name, report_payload)
    else:
        content = json.dumps(report_payload, ensure_ascii=False, indent=2)

    report = Report(
        project_id=project_id,
        generated_by=payload.generated_by,
        format=payload.format,
        payload=report_payload,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return {
        "report_id": report.id,
        "format": report.format,
        "content": content,
    }


@router.get(
    "/projects/{project_id}/reports",
    response_model=list[ReportListRead],
)
async def list_project_reports(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(ResearchProject, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await session.execute(
        select(Report.id, Report.format, Report.created_at)
        .where(Report.project_id == project_id)
        .order_by(Report.created_at, Report.id)
    )
    return [
        {"id": report_id, "format": report_format, "created_at": created_at}
        for report_id, report_format, created_at in result
    ]
