from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import create_source, unique_name


async def test_create_source():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/sources",
            json={"title": unique_name("source"), "url": "https://example.test/source"},
        )

    assert response.status_code == 201
    assert response.json()["id"]


async def test_get_source_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/sources/{uuid4()}")

    assert response.status_code == 404


async def test_get_source():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        source = await create_source(client)
        response = await client.get(f"/sources/{source['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == source["id"]
