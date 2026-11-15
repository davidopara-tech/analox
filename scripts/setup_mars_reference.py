"""Set Mars reference values for climate criteria from NASA publications.

Uses the NASA Goddard Mars Fact Sheet. No API key required.
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models.analox import (
    Candidate, CandidateCharacteristic, ResearchArea, ResearchCriterion,
    ResearchProject, Source,
)

PROJECT_NAME = "African Analogs of Mars — Demo"
MARS_FACT_SHEET = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html"

# name, unit, Mars value, citation
SPECS = [
    ("Mean temperature", "°C", -63.0,
     "NASA Mars Fact Sheet (mean surface temperature)"),
    ("Relative humidity", "%", 0.03,
     "NASA Mars Fact Sheet (atmospheric humidity near zero)"),
    ("Precipitation", "mm/day", 0.0,
     "Mars has no liquid precipitation (NASA)"),
]


async def main():
    async with SessionLocal() as db:
        project = await db.scalar(
            select(ResearchProject).where(ResearchProject.name == PROJECT_NAME)
        )
        if not project:
            print(f"Project {PROJECT_NAME!r} not found.")
            return

        mars_ref = await db.scalar(
            select(Candidate).where(
                Candidate.project_id == project.id,
                Candidate.name.like("Mars Reference%"),
            )
        )
        if not mars_ref:
            print("No Mars Reference candidate.")
            return

        # Source row
        source = await db.scalar(
            select(Source).where(Source.title.like("NASA Mars Reference%"))
        )
        if not source:
            source = Source(
                title="NASA Mars Reference (Fact Sheet)",
                url=MARS_FACT_SHEET,
                citation="NASA Goddard Space Flight Center, Mars Fact Sheet.",
                retrieved_at=datetime.now(timezone.utc),
            )
            db.add(source)
            await db.flush()
            print(f"Created source: {source.title}")

        # Climate area for new criteria
        climate_area = await db.scalar(
            select(ResearchArea).where(
                ResearchArea.project_id == project.id,
                ResearchArea.name == "Climate",
            )
        )
        if not climate_area:
            climate_area = ResearchArea(
                project_id=project.id,
                name="Climate",
                description="Satellite-derived climatology (NASA POWER) and Mars reference values.",
            )
            db.add(climate_area)
            await db.flush()
            print(f"Created area: {climate_area.name}")

        # Reuse existing "Mean temperature" criterion if present
        temp_crit = await db.scalar(
            select(ResearchCriterion)
            .join(ResearchArea, ResearchCriterion.area_id == ResearchArea.id)
            .where(
                ResearchArea.project_id == project.id,
                ResearchCriterion.name == "Mean temperature",
            )
        )

        for name, unit, mars_val, cite in SPECS:
            if name == "Mean temperature" and temp_crit:
                crit = temp_crit
            else:
                crit = await db.scalar(
                    select(ResearchCriterion).where(
                        ResearchCriterion.area_id == climate_area.id,
                        ResearchCriterion.name == name,
                    )
                )
                if not crit:
                    crit = ResearchCriterion(
                        area_id=climate_area.id,
                        name=name,
                        unit=unit,
                        description=f"NASA POWER climate variable.",
                    )
                    db.add(crit)
                    await db.flush()

            existing = await db.scalar(
                select(CandidateCharacteristic).where(
                    CandidateCharacteristic.candidate_id == mars_ref.id,
                    CandidateCharacteristic.criterion_id == crit.id,
                )
            )
            if existing:
                existing.value_numeric = mars_val
                existing.unit = unit
                existing.source_id = source.id
                existing.is_mock = False
                existing.notes = cite
            else:
                db.add(CandidateCharacteristic(
                    candidate_id=mars_ref.id,
                    criterion_id=crit.id,
                    value_numeric=mars_val,
                    unit=unit,
                    source_id=source.id,
                    is_mock=False,
                    notes=cite,
                ))
            print(f"  ✓ {name}: {mars_val} {unit}  (NASA)")

        await db.commit()
        print("\nMars reference updated with real NASA-published values.")
        print("Climate criteria added. Ready for grid discovery.")


if __name__ == "__main__":
    asyncio.run(main())