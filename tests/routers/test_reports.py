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
    unique_name,
)

REFERENCE_CANDIDATE_NAME = "Mars Reference (Literature)"


async def _prepare_report_data(client: AsyncClient) -> tuple[dict, dict]:
    user = await create_user(client)
    workspace = await create_workspace(client, user["id"])
    project = await create_project(client, workspace["id"], user["id"])
    area = await create_area(client, project["id"])
    criterion = await create_criterion(client, area["id"])
    candidate = await create_candidate(client, project["id"])
    reference = await client.post(
        f"/projects/{project['id']}/candidates",
        json={"name": REFERENCE_CANDIDATE_NAME},
    )
    assert reference.status_code == 201, reference.text
    source = await create_source(client)
    characteristic = await client.post(
        f"/candidates/{candidate['id']}/characteristics",
        json={
            "criterion_id": criterion["id"],
            "value_numeric": 3.4,
            "unit": "pH",
            "source_id": source["id"],
            "is_mock": True,
        },
    )
    assert characteristic.status_code == 201, characteristic.text
    finding = await client.post(
        f"/projects/{project['id']}/findings",
        json={
            "candidate_id": candidate["id"],
            "author_id": user["id"],
            "conclusion": unique_name("reviewed finding"),
        },
    )
    assert finding.status_code == 201, finding.text
    reviewed = await client.patch(
        f"/findings/{finding.json()['id']}",
        json={"status": "reviewed"},
    )
    assert reviewed.status_code == 200, reviewed.text
    return project, user


async def test_create_json_report_contains_warning_and_methodology():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project, user = await _prepare_report_data(client)
        response = await client.post(
            f"/projects/{project['id']}/reports",
            json={"format": "json", "generated_by": user["id"]},
        )

    assert response.status_code == 200
    content = response.json()["content"]
    assert '"sample_data_warning": true' in content
    assert "do not constitute scientific confirmation" in content


async def test_create_markdown_report_starts_with_project_heading():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project, user = await _prepare_report_data(client)
        response = await client.post(
            f"/projects/{project['id']}/reports",
            json={"format": "markdown", "generated_by": user["id"]},
        )

    assert response.status_code == 200
    assert response.json()["content"].startswith("# ")
    assert "> **Warning:** This report includes sample/mock data. Not verified." in response.json()["content"]


async def test_list_project_reports_contains_created_report():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project, user = await _prepare_report_data(client)
        created = await client.post(
            f"/projects/{project['id']}/reports",
            json={"format": "json", "generated_by": user["id"]},
        )
        assert created.status_code == 200, created.text
        response = await client.get(f"/projects/{project['id']}/reports")

    assert response.status_code == 200
    assert any(item["id"] == created.json()["report_id"] for item in response.json())
