from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_project,
    create_user,
    create_workspace,
    unique_name,
)


async def test_create_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        response = await client.post(
            f"/workspaces/{workspace['id']}/projects",
            json={
                "name": unique_name("project"),
                "target": "MARS",
                "created_by": user["id"],
            },
        )

    assert response.status_code == 201
    assert response.json()["workspace_id"] == workspace["id"]


async def test_get_project_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/projects/{uuid4()}")

    assert response.status_code == 404


async def test_list_workspace_projects():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        response = await client.get(f"/workspaces/{workspace['id']}/projects")

    assert response.status_code == 200
    assert any(item["id"] == project["id"] for item in response.json())
