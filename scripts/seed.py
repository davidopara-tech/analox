"""Seed ANALOX with labeled sample data.

Every candidate and characteristic is marked is_mock=True and the project
is_sample=True. Safe to re-run — exits if demo data already exists.
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models.analox import (
    Candidate,
    CandidateCharacteristic,
    PlanetTarget,
    ProjectAssignment,
    ProjectStatus,
    ResearchArea,
    ResearchCriterion,
    ResearchProject,
    Source,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

DEMO_EMAIL = "demo@analox.local"


async def seed() -> None:
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing:
            print(f"Demo user already exists ({DEMO_EMAIL}). Skipping seed.")
            return

        user = User(email=DEMO_EMAIL, name="Demo Researcher")
        db.add(user)
        await db.flush()

        workspace = Workspace(name="Hackathon Workspace", created_by=user.id)
        db.add(workspace)
        await db.flush()

        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )
        )

        project = ResearchProject(
            workspace_id=workspace.id,
            name="African Analogs of Mars — Demo",
            description="Sample project. All values are illustrative, not verified.",
            target=PlanetTarget.MARS,
            status=ProjectStatus.ACTIVE,
            is_sample=True,
            created_by=user.id,
        )
        db.add(project)
        await db.flush()

        db.add(
            ProjectAssignment(
                project_id=project.id,
                user_id=user.id,
                task="Review geochemistry criteria for candidate sites.",
                assigned_by=user.id,
            )
        )

        area_geo = ResearchArea(
            project_id=project.id,
            name="Geochemistry",
            description="Aqueous chemistry and salt deposits.",
        )
        area_min = ResearchArea(
            project_id=project.id,
            name="Mineralogy",
            description="Secondary minerals and oxidation state.",
        )
        db.add_all([area_geo, area_min])
        await db.flush()

        crit_ph = ResearchCriterion(area_id=area_geo.id, name="pH", unit="pH")
        crit_temp = ResearchCriterion(
            area_id=area_geo.id,
            name="Mean temperature",
            unit="°C",
        )
        crit_perc = ResearchCriterion(
            area_id=area_geo.id,
            name="Perchlorate presence",
            unit="bool",
        )
        crit_hem = ResearchCriterion(
            area_id=area_min.id,
            name="Hematite fraction",
            unit="%",
        )
        db.add_all([crit_ph, crit_temp, crit_perc, crit_hem])
        await db.flush()

        src_demo = Source(
            title="Illustrative source — NOT a real citation (demo only)",
            url="https://example.com/analox-demo",
            citation="Demo placeholder used for hackathon sample data.",
            retrieved_at=datetime.now(timezone.utc),
        )
        db.add(src_demo)
        await db.flush()

        candidates = [
            Candidate(
                project_id=project.id,
                name="Danakil Depression (Ethiopia)",
                description="Sample record. Hydrothermal, acidic, salt-rich.",
                latitude=14.2417,
                longitude=40.3000,
                region="Afar",
                country="Ethiopia",
                is_mock=True,
            ),
            Candidate(
                project_id=project.id,
                name="Namib Desert (Namibia)",
                description="Sample record. Hyper-arid, oxidizing surface.",
                latitude=-24.7500,
                longitude=15.2833,
                region="Erongo",
                country="Namibia",
                is_mock=True,
            ),
            Candidate(
                project_id=project.id,
                name="Makgadikgadi Pans (Botswana)",
                description="Sample record. Evaporite pan, seasonal water.",
                latitude=-20.6333,
                longitude=25.6167,
                region="Central District",
                country="Botswana",
                is_mock=True,
            ),
        ]
        db.add_all(candidates)
        await db.flush()

        # Sample characteristics for each candidate, all clearly marked mock.
        for candidate in candidates:
            db.add_all(
                [
                    CandidateCharacteristic(
                        candidate_id=candidate.id,
                        criterion_id=crit_ph.id,
                        value_numeric=2.1,
                        unit="pH",
                        source_id=src_demo.id,
                        is_mock=True,
                        notes="Sample value, not measured.",
                    ),
                    CandidateCharacteristic(
                        candidate_id=candidate.id,
                        criterion_id=crit_temp.id,
                        value_numeric=32.0,
                        unit="°C",
                        source_id=src_demo.id,
                        is_mock=True,
                        notes="Sample value, not measured.",
                    ),
                    CandidateCharacteristic(
                        candidate_id=candidate.id,
                        criterion_id=crit_perc.id,
                        value_text="unknown",
                        source_id=src_demo.id,
                        is_mock=True,
                        notes="Unknown — no sample data.",
                    ),
                    CandidateCharacteristic(
                        candidate_id=candidate.id,
                        criterion_id=crit_hem.id,
                        value_numeric=5.0,
                        unit="%",
                        source_id=src_demo.id,
                        is_mock=True,
                        notes="Sample value, not measured.",
                    ),
                ]
            )

        await db.commit()
        print(f"Seeded. Project id: {project.id}")
        print(f"Demo user: {DEMO_EMAIL}")
        print("All candidates/characteristics marked is_mock=True; project is_sample=True.")


if __name__ == "__main__":
    asyncio.run(seed())
