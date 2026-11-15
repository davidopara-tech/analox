from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.routers._helpers import create_user, unique_name


async def test_create_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/users",
            json={"email": f"{uuid4().hex}@example.test", "name": unique_name("user")},
        )

    assert response.status_code == 201
    assert response.json()["id"]


async def test_get_user_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/users/{uuid4()}")

    assert response.status_code == 404


async def test_list_users():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await create_user(client)
        limit = 500
        offset = 0
        found = False
        while True:
            response = await client.get(
                "/users",
                params={"limit": limit, "offset": offset},
            )
            assert response.status_code == 200
            page = response.json()
            if any(item["id"] == user["id"] for item in page):
                found = True
                break
            if len(page) < limit:
                break
            offset += limit

    assert found
