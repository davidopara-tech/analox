from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_candidate,
    create_project,
    create_user,
    create_workspace,
)


async def _create_finding(client: AsyncClient) -> tuple[dict, dict]:
    author = await create_user(client)
    workspace = await create_workspace(client, author["id"])
    project = await create_project(client, workspace["id"], author["id"])
    candidate = await create_candidate(client, project["id"])
    response = await client.post(
        f"/projects/{project['id']}/findings",
        json={
            "candidate_id": candidate["id"],
            "author_id": author["id"],
            "conclusion": "Review this sample finding.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json(), project


async def test_create_finding_always_starts_draft():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        author = await create_user(client)
        workspace = await create_workspace(client, author["id"])
        project = await create_project(client, workspace["id"], author["id"])
        candidate = await create_candidate(client, project["id"])
        response = await client.post(
            f"/projects/{project['id']}/findings",
            json={
                "candidate_id": candidate["id"],
                "author_id": author["id"],
                "conclusion": "A test conclusion.",
                "status": "reviewed",
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "draft"


async def test_patch_draft_to_reviewed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        finding, _ = await _create_finding(client)
        response = await client.patch(
            f"/findings/{finding['id']}",
            json={"status": "reviewed"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "reviewed"


async def test_patch_reviewed_to_draft_is_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        finding, _ = await _create_finding(client)
        reviewed = await client.patch(
            f"/findings/{finding['id']}",
            json={"status": "reviewed"},
        )
        assert reviewed.status_code == 200, reviewed.text
        response = await client.patch(
            f"/findings/{finding['id']}",
            json={"status": "draft"},
        )

    assert response.status_code == 400


async def test_patch_draft_to_draft_is_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        finding, _ = await _create_finding(client)
        response = await client.patch(
            f"/findings/{finding['id']}",
            json={"status": "draft"},
        )

    assert response.status_code == 400


async def test_patch_unknown_finding_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/findings/{uuid4()}",
            json={"status": "reviewed"},
        )

    assert response.status_code == 404
