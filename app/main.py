from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.routers import consensus as consensus_router
from app.db import get_session
from app.routers import findings, reports

app = FastAPI(title="ANALOX API")

router = APIRouter(prefix="/api", tags=["ANALOX API"])

REQUIRED_EXTENSIONS = {"vector"}



@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        result = await session.execute(text("SELECT extname FROM pg_extension"))
        extensions = sorted(row[0] for row in result)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc

    missing = REQUIRED_EXTENSIONS - set(extensions)
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"missing required extensions: {sorted(missing)}",
        )

    return {"status": "ok", "database": "ok", "extensions": extensions}

from app.routers import (
    areas, assignments, candidates, characteristics, criteria,
    projects, sources, users, workspaces,
)

app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(projects.workspace_projects_router)
app.include_router(projects.projects_router)
app.include_router(areas.router)
app.include_router(criteria.router)
app.include_router(assignments.router)
app.include_router(candidates.project_candidates_router)
app.include_router(candidates.candidates_router)
app.include_router(sources.router)
app.include_router(characteristics.router)
app.include_router(consensus_router.router)
app.include_router(findings.router)
app.include_router(reports.router)
from app.routers import discovery as discovery_router
app.include_router(discovery_router.router)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")