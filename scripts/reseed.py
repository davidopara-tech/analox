"""Reseed candidates for demo. Adds Mars Reference candidate."""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models.analox import (
    Candidate, CandidateCharacteristic, ResearchArea, ResearchCriterion,
    ResearchProject, Source,
)

PROJECT_NAME = "African Analogs of Mars — Demo"


async def main() -> None:
    async with SessionLocal() as db:
        project = await db.scalar(
            select(ResearchProject).where(ResearchProject.name == PROJECT_NAME)
        )
        if not project:
            print(f"Project {PROJECT_NAME!r} not found — run scripts/seed.py first.")
            return

        await db.execute(delete(Candidate).where(Candidate.project_id == project.id))

        crit_rows = (await db.execute(
            select(ResearchCriterion).join(ResearchArea)
            .where(ResearchArea.project_id == project.id)
        )).scalars().all()
        by_name = {c.name: c for c in crit_rows}

        required = {"pH", "Mean temperature", "Perchlorate presence", "Hematite fraction"}
        if not required.issubset(by_name):
            print(f"Missing criteria: {required - set(by_name)}")
            return

        # name, description, lat, lon, region, country, {criterion: value}
        entries = [
            ("Danakil Depression (Ethiopia)",
             "Hydrothermal, hyperacidic, salt-rich. Sample demo values.",
             14.2417, 40.3000, "Afar", "Ethiopia",
             {"pH": 0.5, "Mean temperature": 34.5,
              "Perchlorate presence": 1.0, "Hematite fraction": 2.0}),
            ("Namib Desert (Namibia)",
             "Hyperarid, oxidizing, hematite-bearing. Sample demo values.",
             -24.7500, 15.2833, "Erongo", "Namibia",
             {"pH": 8.5, "Mean temperature": 25.0,
              "Perchlorate presence": 0.0, "Hematite fraction": 8.0}),
            ("Lake Natron (Tanzania)",
             "Hyperalkaline soda lake, evaporites. Sample demo values.",
             -2.4167, 36.0000, "Arusha", "Tanzania",
             {"pH": 10.5, "Mean temperature": 30.0,
              "Perchlorate presence": 0.0, "Hematite fraction": 1.5}),
            ("Makgadikgadi Pans (Botswana)",
             "Evaporite pan, seasonal water. Sample demo values.",
             -20.6333, 25.6167, "Central District", "Botswana",
             {"pH": 9.0, "Mean temperature": 24.0,
              "Perchlorate presence": 0.0, "Hematite fraction": 3.0}),
            ("Mars Reference (Literature)",
             "Reference values used for consensus. Sample placeholders.",
             None, None, None, None,
             {"pH": 6.5, "Mean temperature": -60.0,
              "Perchlorate presence": 1.0, "Hematite fraction": 12.0}),
        ]

        for name, desc, lat, lon, region, country, values in entries:
            src = Source(
                title=f"Sample source — {name}",
                url="https://example.com/analox-demo",
                citation="Demo placeholder — not a real publication.",
                retrieved_at=datetime.now(timezone.utc),
            )
            db.add(src)
            await db.flush()

            cand = Candidate(
                project_id=project.id, name=name, description=desc,
                latitude=lat, longitude=lon, region=region, country=country,
                is_mock=True,
            )
            db.add(cand)
            await db.flush()

            for cname, val in values.items():
                crit = by_name[cname]
                db.add(CandidateCharacteristic(
                    candidate_id=cand.id, criterion_id=crit.id,
                    value_numeric=val, unit=crit.unit,
                    source_id=src.id, is_mock=True,
                    notes="Sample demo value. Not measured.",
                ))

        await db.commit()
        print(f"Reseeded {len(entries)} candidates.")
        print(f"Project id: {project.id}")
        print("Mars Reference candidate added — consensus is now computable.")


if __name__ == "__main__":
    asyncio.run(main())