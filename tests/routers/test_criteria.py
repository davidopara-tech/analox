from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_area,
    create_criterion,
    create_project,
    create_user,
    create_workspace,
    unique_name,
)


async def test_create_criterion():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        area = await create_area(client, project["id"])
        response = await client.post(
            f"/areas/{area['id']}/criteria",
            json={"name": unique_name("criterion"), "description": "Acidity", "unit": "pH"},
        )

    assert response.status_code == 201
    assert response.json()["area_id"] == area["id"]


async def test_list_criteria():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        area = await create_area(client, project["id"])
        criterion = await create_criterion(client, area["id"])
        response = await client.get(f"/areas/{area['id']}/criteria")

    assert response.status_code == 200
    assert any(item["id"] == criterion["id"] for item in response.json())
