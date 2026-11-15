from uuid import uuid4

from httpx import AsyncClient


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


async def create_user(client: AsyncClient) -> dict:
    response = await client.post(
        "/users",
        json={
            "email": f"{uuid4().hex}@example.test",
            "name": unique_name("user"),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_workspace(client: AsyncClient, created_by: str) -> dict:
    response = await client.post(
        "/workspaces",
        json={"name": unique_name("workspace"), "created_by": created_by},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_project(client: AsyncClient, workspace_id: str, created_by: str) -> dict:
    response = await client.post(
        f"/workspaces/{workspace_id}/projects",
        json={
            "name": unique_name("project"),
            "description": "Integration test project.",
            "target": "MARS",
            "created_by": created_by,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_area(client: AsyncClient, project_id: str) -> dict:
    response = await client.post(
        f"/projects/{project_id}/areas",
        json={"name": unique_name("area"), "description": "Integration test area."},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_criterion(client: AsyncClient, area_id: str) -> dict:
    response = await client.post(
        f"/areas/{area_id}/criteria",
        json={"name": unique_name("criterion"), "description": None, "unit": "test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_candidate(client: AsyncClient, project_id: str) -> dict:
    response = await client.post(
        f"/projects/{project_id}/candidates",
        json={"name": unique_name("candidate"), "country": "Testland"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_source(client: AsyncClient) -> dict:
    response = await client.post(
        "/sources",
        json={"title": unique_name("source"), "citation": "Integration test source."},
    )
    assert response.status_code == 201, response.text
    return response.json()
