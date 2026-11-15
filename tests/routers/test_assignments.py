from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_project,
    create_user,
    create_workspace,
    unique_name,
)


async def test_create_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        response = await client.post(
            f"/projects/{project['id']}/assignments",
            json={
                "user_id": user["id"],
                "task": unique_name("task"),
                "assigned_by": user["id"],
            },
        )

    assert response.status_code == 201
    assert response.json()["assigned_by"] == user["id"]


async def test_list_assignments():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        assignment = await client.post(
            f"/projects/{project['id']}/assignments",
            json={"user_id": user["id"], "task": "Review", "assigned_by": user["id"]},
        )
        assert assignment.status_code == 201, assignment.text
        response = await client.get(f"/projects/{project['id']}/assignments")

    assert response.status_code == 200
    assert any(item["id"] == assignment.json()["id"] for item in response.json())
