"""Ingest real annual mean temperature from NASA POWER for candidate sites.

NASA POWER (Prediction Of Worldwide Energy Resources) is a NASA Langley
dataset derived from MERRA-2 and CERES. No API key, no account required.
Source: https://power.larc.nasa.gov/
"""
import asyncio
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models.analox import (
    Candidate, CandidateCharacteristic, ResearchArea, ResearchCriterion,
    ResearchProject, Source,
)

PROJECT_NAME = "African Analogs of Mars — Demo"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
POWER_CITATION = (
    "NASA POWER (Prediction Of Worldwide Energy Resources) Project, "
    "NASA Langley Research Center. Satellite-derived climatology, "
    "parameter T2M (temperature at 2 m, °C), annual mean."
)


async def fetch_annual_temp(lat: float, lon: float) -> float:
    params = {
        "parameters": "T2M",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "format": "JSON",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(POWER_URL, params=params)
        r.raise_for_status()
        data = r.json()
    return float(data["properties"]["parameter"]["T2M"]["ANN"])


async def main() -> None:
    async with SessionLocal() as db:
        project = await db.scalar(
            select(ResearchProject).where(ResearchProject.name == PROJECT_NAME)
        )
        if not project:
            print(f"Project {PROJECT_NAME!r} not found.")
            return

        temp_crit = await db.scalar(
            select(ResearchCriterion)
            .join(ResearchArea)
            .where(
                ResearchArea.project_id == project.id,
                ResearchCriterion.name == "Mean temperature",
            )
        )
        if not temp_crit:
            print("No 'Mean temperature' criterion in this project.")
            return

        source = await db.scalar(
            select(Source).where(Source.title.like("NASA POWER%"))
        )
        if not source:
            source = Source(
                title="NASA POWER — Annual Mean Temperature (T2M)",
                url="https://power.larc.nasa.gov/",
                citation=POWER_CITATION,
                retrieved_at=datetime.now(timezone.utc),
            )
            db.add(source)
            await db.flush()
            print(f"Created source: {source.title}")

        candidates = (await db.execute(
            select(Candidate).where(
                Candidate.project_id == project.id,
                Candidate.name != "Mars Reference (Literature)",
                Candidate.latitude.is_not(None),
                Candidate.longitude.is_not(None),
            )
        )).scalars().all()

        for cand in candidates:
            try:
                temp_c = await fetch_annual_temp(cand.latitude, cand.longitude)
            except Exception as e:
                print(f"  ✗ {cand.name}: {e}")
                continue

            existing = await db.scalar(
                select(CandidateCharacteristic).where(
                    CandidateCharacteristic.candidate_id == cand.id,
                    CandidateCharacteristic.criterion_id == temp_crit.id,
                )
            )
            if existing:
                existing.value_numeric = temp_c
                existing.unit = "°C"
                existing.source_id = source.id
                existing.is_mock = False
                existing.notes = "Real value from NASA POWER (T2M annual mean)."
            else:
                db.add(CandidateCharacteristic(
                    candidate_id=cand.id,
                    criterion_id=temp_crit.id,
                    value_numeric=temp_c,
                    unit="°C",
                    source_id=source.id,
                    is_mock=False,
                    notes="Real value from NASA POWER (T2M annual mean).",
                ))
            print(f"  ✓ {cand.name}: {temp_c:.1f} °C  (NASA POWER)")

        await db.commit()
        print("\nDone. 'Mean temperature' now holds real NASA POWER data.")
        print("Other criteria remain is_mock=True.")


if __name__ == "__main__":
    asyncio.run(main())