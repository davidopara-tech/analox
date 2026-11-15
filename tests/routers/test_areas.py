from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_area,
    create_project,
    create_user,
    create_workspace,
    unique_name,
)


async def test_create_area():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        response = await client.post(
            f"/projects/{project['id']}/areas",
            json={"name": unique_name("area"), "description": "Integration test."},
        )

    assert response.status_code == 201
    assert response.json()["project_id"] == project["id"]


async def test_list_areas():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        area = await create_area(client, project["id"])
        response = await client.get(f"/projects/{project['id']}/areas")

    assert response.status_code == 200
    assert any(item["id"] == area["id"] for item in response.json())
