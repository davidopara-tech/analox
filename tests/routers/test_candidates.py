from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_candidate,
    create_project,
    create_user,
    create_workspace,
    unique_name,
)


async def test_create_candidate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        response = await client.post(
            f"/projects/{project['id']}/candidates",
            json={
                "name": unique_name("candidate"),
                "latitude": 10.5,
                "longitude": -20.25,
                "country": "Testland",
            },
        )

    assert response.status_code == 201
    assert response.json()["project_id"] == project["id"]


async def test_get_candidate_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/candidates/{uuid4()}")

    assert response.status_code == 404


async def test_list_candidates():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        candidate = await create_candidate(client, project["id"])
        response = await client.get(f"/projects/{project['id']}/candidates")

    assert response.status_code == 200
    assert any(item["id"] == candidate["id"] for item in response.json())
