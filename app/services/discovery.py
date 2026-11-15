"""Grid-based discovery of terrestrial analogs via NASA POWER.

Scans a lat/lon grid over Africa, fetches satellite-derived climatology
from NASA POWER for each cell, scores against the Mars reference, and
inserts the top matches as new candidates.
"""
import asyncio
import math
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analox import (
    Candidate, CandidateCharacteristic, ResearchArea, ResearchCriterion,
    Source,
)

POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"


async def _fetch_power(client, lat, lon):
    params = {
        "parameters": "T2M,RH2M,PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "format": "JSON",
    }
    r = await client.get(POWER_URL, params=params, timeout=30)
    r.raise_for_status()
    p = r.json()["properties"]["parameter"]
    return {
        "Mean temperature": p.get("T2M", {}).get("ANN"),
        "Relative humidity": p.get("RH2M", {}).get("ANN"),
        "Precipitation": p.get("PRECTOTCORR", {}).get("ANN"),
    }


async def discover_analogs(
    db: AsyncSession,
    project_id: uuid.UUID,
    lat_min: float = -35.0,
    lat_max: float = 37.0,
    lon_min: float = -18.0,
    lon_max: float = 51.0,
    spacing: float = 4.0,
    top_n: int = 10,
    concurrency: int = 8,
) -> dict:
    # 1. Resolve climate criteria (must already exist from setup script)
    mars_ref = await db.scalar(
        select(Candidate).where(
            Candidate.project_id == project_id,
            Candidate.name.like("Mars Reference%"),
        )
    )
    if not mars_ref:
        raise ValueError("No Mars Reference candidate in this project.")

    # Fetch all criteria attached to Mars reference
    mars_chars = (await db.execute(
        select(CandidateCharacteristic, ResearchCriterion)
        .join(ResearchCriterion,
              CandidateCharacteristic.criterion_id == ResearchCriterion.id)
        .where(
            CandidateCharacteristic.candidate_id == mars_ref.id,
            ResearchCriterion.name.in_(
                ["Mean temperature", "Relative humidity", "Precipitation"]
            ),
        )
    )).all()
    if not mars_chars:
        raise ValueError(
            "Mars reference has no climate values. Run scripts/setup_mars_reference.py first."
        )

    criteria_map = {}  # name -> (criterion, mars_value)
    for ch, crit in mars_chars:
        if ch.value_numeric is not None:
            criteria_map[crit.name] = (crit, ch.value_numeric)

    if len(criteria_map) < 2:
        raise ValueError("Need at least 2 climate criteria on Mars reference.")

    # 2. Build grid
    cells = []
    lat = lat_min
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            cells.append((round(lat, 2), round(lon, 2)))
            lon += spacing
        lat += spacing

    # 3. Fetch with bounded concurrency
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        async def fetch_one(la, lo):
            async with sem:
                try:
                    return (la, lo, await _fetch_power(client, la, lo))
                except Exception:
                    return (la, lo, None)
        results = await asyncio.gather(*[fetch_one(la, lo) for la, lo in cells])

    # 4. Filter: drop ocean (humidity > 80%) and nulls
    valid = []
    for lat_, lon_, vals in results:
        if vals is None:
            continue
        rh = vals.get("Relative humidity")
        if rh is not None and rh > 80:
            continue  # likely ocean
        if vals.get("Mean temperature") is None:
            continue
        valid.append((lat_, lon_, vals))

    if not valid:
        return {
            "scanned": len(cells), "kept": 0, "inserted": 0,
            "new_candidates": [],
            "message": "No valid land cells returned from NASA POWER.",
        }

    # 5. Min-max ranges per criterion (over cells + Mars reference)
    ranges = {}
    for name, (crit, mars_val) in criteria_map.items():
        vals = [v[name] for _, _, v in valid if v.get(name) is not None]
        vals.append(mars_val)
        if len(vals) >= 2:
            ranges[name] = (min(vals), max(vals))

    def scaled(name, value):
        if value is None or name not in ranges:
            return None
        mn, mx = ranges[name]
        return 0.5 if mx == mn else (value - mn) / (mx - mn)

    # 6. Score (L2 in scaled space, same as consensus engine)
    scored = []
    for lat_, lon_, vals in valid:
        diffs = []
        for name, (crit, mars_val) in criteria_map.items():
            m_s = scaled(name, mars_val)
            v_s = scaled(name, vals.get(name))
            if m_s is None or v_s is None:
                continue
            diffs.append((v_s - m_s) ** 2)
        if not diffs:
            continue
        distance = math.sqrt(sum(diffs))
        max_d = math.sqrt(len(diffs))
        score = round(1.0 - (distance / max_d), 4) if max_d > 0 else 0.0
        scored.append({"lat": lat_, "lon": lon_, "score": score, "values": vals})

    scored.sort(key=lambda x: -x["score"])
    top = scored[:top_n]

    # 7. Source row for discovered cells
    source = await db.scalar(
        select(Source).where(Source.title.like("NASA POWER — Satellite%"))
    )
    if not source:
        source = Source(
            title="NASA POWER — Satellite-Derived Climatology",
            url="https://power.larc.nasa.gov/",
            citation=(
                "NASA POWER (Prediction Of Worldwide Energy Resources), "
                "NASA Langley Research Center. Parameters T2M, RH2M, PRECTOTCORR."
            ),
            retrieved_at=datetime.now(timezone.utc),
        )
        db.add(source)
        await db.flush()

    # 8. Insert top N (dedupe by name)
    inserted = []
    for entry in top:
        cand_name = f"Auto · {entry['lat']:.1f}°, {entry['lon']:.1f}°"
        existing = await db.scalar(
            select(Candidate).where(
                Candidate.project_id == project_id,
                Candidate.name == cand_name,
            )
        )
        if existing:
            continue
        cand = Candidate(
            project_id=project_id,
            name=cand_name,
            description=(
                f"Auto-discovered by NASA POWER grid scan. "
                f"Similarity to Mars: {entry['score']:.3f}."
            ),
            latitude=entry["lat"],
            longitude=entry["lon"],
            is_mock=False,
        )
        db.add(cand)
        await db.flush()
        for name, (crit, _mars_val) in criteria_map.items():
            val = entry["values"].get(name)
            if val is None:
                continue
            db.add(CandidateCharacteristic(
                candidate_id=cand.id,
                criterion_id=crit.id,
                value_numeric=val,
                unit=crit.unit,
                source_id=source.id,
                is_mock=False,
                notes="Auto-discovered via NASA POWER grid scan.",
            ))
        inserted.append({
            "candidate_id": str(cand.id),
            "name": cand.name,
            "latitude": entry["lat"],
            "longitude": entry["lon"],
            "score": entry["score"],
            "characteristics": entry["values"],
        })

    await db.commit()
    return {
        "scanned": len(cells),
        "kept": len(valid),
        "inserted": len(inserted),
        "new_candidates": inserted,
    }