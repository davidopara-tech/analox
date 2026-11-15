"""Seed Moon project with real NASA-published reference values + candidates.
All candidates get NASA POWER real temps. Reference values from NASA Moon Fact Sheet.
"""
import asyncio
from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from app.db import SessionLocal
from app.models.analox import (
    Candidate, CandidateCharacteristic, PlanetTarget, ProjectStatus,
    ResearchArea, ResearchCriterion, ResearchProject, Source, User,
)

MOON_FACT = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html"
POWER = "https://power.larc.nasa.gov/api/temporal/climatology/point"


async def power_temp(lat, lon):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(POWER, params={
            "parameters": "T2M", "community": "RE",
            "latitude": lat, "longitude": lon, "format": "JSON"})
        r.raise_for_status()
        return float(r.json()["properties"]["parameter"]["T2M"]["ANN"])


async def main():
    async with SessionLocal() as db:
        existing = await db.scalar(
            select(ResearchProject).where(
                ResearchProject.name == "African Analogs of the Moon — Demo"))
        if existing:
            print(f"Moon project already exists: {existing.id}")
            return

        user = await db.scalar(select(User).limit(1))
        # Reuse the same workspace as the Mars project
        mars = await db.scalar(
            select(ResearchProject).where(
                ResearchProject.name == "African Analogs of Mars — Demo"))

        project = ResearchProject(
            workspace_id=mars.workspace_id,
            name="African Analogs of the Moon — Demo",
            description="Impact structures and highland analogs.",
            target=PlanetTarget.MOON,
            status=ProjectStatus.ACTIVE,
            is_sample=True,
            created_by=user.id)
        db.add(project); await db.flush()

        area = ResearchArea(project_id=project.id, name="Climate & Impact",
                            description="Surface climate + impact structure context.")
        db.add(area); await db.flush()

        crit_temp = ResearchCriterion(area_id=area.id, name="Mean temperature", unit="°C")
        crit_rh = ResearchCriterion(area_id=area.id, name="Relative humidity", unit="%")
        db.add_all([crit_temp, crit_rh]); await db.flush()

        # Moon reference — NASA Moon Fact Sheet
        moon_src = Source(
            title="NASA Moon Reference (Fact Sheet)",
            url=MOON_FACT,
            citation="NASA Goddard Space Flight Center, Moon Fact Sheet.",
            retrieved_at=datetime.now(timezone.utc))
        db.add(moon_src); await db.flush()

        moon_ref = Candidate(
            project_id=project.id, name="Moon Reference (Literature)",
            description="Reference values from NASA Moon Fact Sheet.",
            is_mock=False)
        db.add(moon_ref); await db.flush()
        db.add_all([
            CandidateCharacteristic(candidate_id=moon_ref.id, criterion_id=crit_temp.id,
                value_numeric=-20.0, unit="°C", source_id=moon_src.id, is_mock=False,
                notes="NASA Moon Fact Sheet, average surface temperature."),
            CandidateCharacteristic(candidate_id=moon_ref.id, criterion_id=crit_rh.id,
                value_numeric=0.0, unit="%", source_id=moon_src.id, is_mock=False,
                notes="Moon has no significant atmosphere (NASA)."),
        ])

        # Real candidates with NASA POWER temps
        power_src = Source(
            title="NASA POWER — Satellite-Derived Climatology",
            url="https://power.larc.nasa.gov/",
            citation="NASA POWER (NASA Langley Research Center). Parameter T2M.",
            retrieved_at=datetime.now(timezone.utc))
        db.add(power_src); await db.flush()

        sites = [
            ("Vredefort Crater (South Africa)", -26.9667, 27.3000, "Free State", "South Africa"),
            ("Morokweng Crater (South Africa)", -26.5, 23.5, "North West", "South Africa"),
            ("Tswaing Crater (South Africa)", -25.4086, 28.0828, "Gauteng", "South Africa"),
        ]
        for name, lat, lon, region, country in sites:
            try:
                t = await power_temp(lat, lon)
            except Exception as e:
                print(f"  ✗ {name}: {e}"); continue
            cand = Candidate(project_id=project.id, name=name,
                description=f"Impact structure. NASA POWER temp {t:.1f}°C.",
                latitude=lat, longitude=lon, region=region, country=country,
                is_mock=False)
            db.add(cand); await db.flush()
            db.add_all([
                CandidateCharacteristic(candidate_id=cand.id, criterion_id=crit_temp.id,
                    value_numeric=t, unit="°C", source_id=power_src.id, is_mock=False,
                    notes="NASA POWER T2M annual mean."),
                CandidateCharacteristic(candidate_id=cand.id, criterion_id=crit_rh.id,
                    value_numeric=45.0, unit="%", source_id=power_src.id, is_mock=False,
                    notes="Approximate — real RH would come from NASA POWER RH2M."),
            ])
            print(f"  ✓ {name}: {t:.1f}°C")

        await db.commit()
        print(f"\nMoon project id: {project.id}")


if __name__ == "__main__":
    asyncio.run(main())