from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import (
    create_area,
    create_candidate,
    create_criterion,
    create_project,
    create_source,
    create_user,
    create_workspace,
)


async def test_create_characteristic():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        area = await create_area(client, project["id"])
        criterion = await create_criterion(client, area["id"])
        candidate = await create_candidate(client, project["id"])
        source = await create_source(client)
        response = await client.post(
            f"/candidates/{candidate['id']}/characteristics",
            json={
                "criterion_id": criterion["id"],
                "value_numeric": 3.5,
                "unit": "pH",
                "source_id": source["id"],
                "is_mock": True,
            },
        )

    assert response.status_code == 201
    assert response.json()["source_id"] == source["id"]
    assert response.json()["is_mock"] is True


async def test_list_characteristics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        workspace = await create_workspace(client, user["id"])
        project = await create_project(client, workspace["id"], user["id"])
        area = await create_area(client, project["id"])
        criterion = await create_criterion(client, area["id"])
        candidate = await create_candidate(client, project["id"])
        source = await create_source(client)
        characteristic = await client.post(
            f"/candidates/{candidate['id']}/characteristics",
            json={
                "criterion_id": criterion["id"],
                "value_text": "measured later",
                "source_id": source["id"],
                "is_mock": True,
            },
        )
        assert characteristic.status_code == 201, characteristic.text
        response = await client.get(
            f"/candidates/{candidate['id']}/characteristics"
        )

    assert response.status_code == 200
    assert any(
        item["id"] == characteristic.json()["id"]
        for item in response.json()
    )
