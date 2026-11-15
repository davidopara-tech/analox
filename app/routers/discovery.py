import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.analox import (
    Candidate,
    CandidateCharacteristic,
    ResearchArea,
    ResearchCriterion,
    ResearchProject,
    Source,
)
from app.services.discovery import discover_analogs

router = APIRouter(prefix="/projects/{project_id}", tags=["discovery"])


class DiscoverBody(BaseModel):
    lat_min: float = -35.0
    lat_max: float = 37.0
    lon_min: float = -18.0
    lon_max: float = 51.0
    spacing: float = Field(default=4.0, ge=1.0, le=15.0)
    top_n: int = Field(default=10, ge=1, le=30)


class CoordinateBody(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    name: str | None = None


@router.post("/discover")
async def post_discover(
    project_id: uuid.UUID,
    body: DiscoverBody | None = None,
    session: AsyncSession = Depends(get_session),
):
    body = body or DiscoverBody()
    try:
        return await discover_analogs(
            session, project_id,
            lat_min=body.lat_min, lat_max=body.lat_max,
            lon_min=body.lon_min, lon_max=body.lon_max,
            spacing=body.spacing, top_n=body.top_n,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/discover-coordinate")
async def post_discover_coordinate(
    project_id: uuid.UUID,
    body: CoordinateBody,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    climate_criteria = (
        await session.execute(
            select(ResearchCriterion)
            .join(ResearchArea, ResearchCriterion.area_id == ResearchArea.id)
            .where(
                ResearchArea.project_id == project_id,
                ResearchCriterion.name.in_(
                    ["Mean temperature", "Relative humidity", "Precipitation"]
                ),
            )
        )
    ).scalars().all()
    if not climate_criteria:
        raise HTTPException(status_code=400, detail="No climate criteria in this project.")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://power.larc.nasa.gov/api/temporal/climatology/point",
                params={
                    "parameters": "T2M,RH2M,PRECTOTCORR",
                    "community": "AG",
                    "latitude": body.latitude,
                    "longitude": body.longitude,
                    "format": "JSON",
                },
                timeout=30,
            )
            response.raise_for_status()
            params = response.json()["properties"]["parameter"]
            values = {
                "Mean temperature": params.get("T2M", {}).get("ANN"),
                "Relative humidity": params.get("RH2M", {}).get("ANN"),
                "Precipitation": params.get("PRECTOTCORR", {}).get("ANN"),
            }
    except (httpx.HTTPError, AttributeError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"NASA POWER unavailable or returned invalid data: {exc}",
        ) from exc

    source = await session.scalar(
        select(Source).where(Source.title.like("NASA POWER — Satellite%"))
    )
    if source is None:
        source = Source(
            title="NASA POWER — Satellite-Derived Climatology",
            url="https://power.larc.nasa.gov/",
            citation="NASA POWER (NASA Langley Research Center).",
            retrieved_at=datetime.now(timezone.utc),
        )
        session.add(source)
        await session.flush()

    name = body.name.strip() if body.name and body.name.strip() else (
        f"Custom · {body.latitude:.2f}, {body.longitude:.2f}"
    )
    candidate = Candidate(
        project_id=project_id,
        name=name,
        description="User-requested location. NASA POWER data.",
        latitude=body.latitude,
        longitude=body.longitude,
        is_mock=False,
    )
    session.add(candidate)
    await session.flush()

    for criterion in climate_criteria:
        value = values.get(criterion.name)
        if value is not None:
            session.add(
                CandidateCharacteristic(
                    candidate_id=candidate.id,
                    criterion_id=criterion.id,
                    value_numeric=value,
                    unit=criterion.unit,
                    source_id=source.id,
                    is_mock=False,
                    notes="NASA POWER annual mean.",
                )
            )

    await session.commit()
    return {
        "candidate_id": str(candidate.id),
        "name": candidate.name,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "values": values,
    }