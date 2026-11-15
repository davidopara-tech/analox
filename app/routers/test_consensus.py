import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.analox import ResearchProject


async def test_consensus_404_for_unknown_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/projects/{uuid.uuid4()}/consensus")
    assert response.status_code == 404


async def test_consensus_happy_path():
    async with SessionLocal() as db:
        project = await db.scalar(
            select(ResearchProject).where(
                ResearchProject.name == "African Analogs of Mars — Demo"
            )
        )
    assert project is not None, "Run scripts/reseed.py before tests."

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/projects/{project.id}/consensus")

    assert response.status_code == 200
    body = response.json()
    assert body["reference_candidate_name"] == "Mars Reference (Literature)"
    assert len(body["results"]) == 4  # Danakil, Namib, Natron, Makgadikgadi
    top = body["results"][0]
    assert top["total"] is not None
    # Decomposability — each result must show per-area and per-criterion breakdown
    assert len(top["per_area"]) == 2  # Geochemistry + Mineralogy
    assert len(top["per_criterion"]) >= 1