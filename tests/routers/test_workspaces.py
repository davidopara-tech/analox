from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import create_user, unique_name


async def test_create_workspace():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        response = await client.post(
            "/workspaces",
            json={"name": unique_name("workspace"), "created_by": user["id"]},
        )

    assert response.status_code == 201
    assert response.json()["created_by"] == user["id"]


async def test_get_workspace_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/workspaces/{uuid4()}")

    assert response.status_code == 404


async def test_add_workspace_member():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner = await create_user(client)
        member = await create_user(client)
        workspace = await client.post(
            "/workspaces",
            json={"name": unique_name("workspace"), "created_by": owner["id"]},
        )
        assert workspace.status_code == 201, workspace.text
        response = await client.post(
            f"/workspaces/{workspace.json()['id']}/members",
            json={"user_id": member["id"], "role": "member"},
        )

    assert response.status_code == 201
    assert response.json()["user_id"] == member["id"]
