"""Weighted multi-perspective consensus — the Cochee port.

Each research area is a "perspective". For each perspective, we compute
the L2 distance in min-max scaled criterion space between a candidate
and the Mars Reference candidate. That distance becomes a similarity
score in [0, 1]. Total = weighted average across perspectives.

Design notes (matches the Cochee blueprint and ANALOX philosophy):
- Min-max scaling is per criterion, across all candidates + reference.
- L2 distance is used because vectors are bounded to [0, 1] per dim.
- Weights are passed per query, never stored.
- The response is fully decomposable: total, per-area, per-criterion.
- Missing values do NOT become zero. A criterion is only used when both
  the candidate and the reference have a value for it.
"""
import math
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analox import (
    Candidate,
    CandidateCharacteristic,
    ResearchArea,
    ResearchCriterion,
    ResearchProject,
)

REFERENCE_NAME = "Mars Reference (Literature)"


class ConsensusError(Exception):
    """Raised when consensus cannot be computed (404 or 400)."""


def _kind(msg: str) -> int:
    return 404 if "not found" in msg or "no reference" in msg else 400


async def compute_consensus(
    db: AsyncSession,
    project_id: uuid.UUID,
    weights: dict[str, float] | None = None,
) -> dict:
    project = await db.get(ResearchProject, project_id)
    if project is None:
        raise ConsensusError("project not found")

    reference = await db.scalar(
        select(Candidate).where(
            Candidate.project_id == project_id,
            Candidate.name == REFERENCE_NAME,
        )
    )
    if reference is None:
        raise ConsensusError(
            f"no reference candidate named {REFERENCE_NAME!r} in this project"
        )

    areas = (await db.execute(
        select(ResearchArea).where(ResearchArea.project_id == project_id)
    )).scalars().all()
    if not areas:
        raise ConsensusError("project has no research areas")

    area_ids = [a.id for a in areas]
    criteria = (await db.execute(
        select(ResearchCriterion).where(ResearchCriterion.area_id.in_(area_ids))
    )).scalars().all()
    if not criteria:
        raise ConsensusError("project areas have no research criteria")

    criteria_by_area: dict[uuid.UUID, list[ResearchCriterion]] = defaultdict(list)
    for c in criteria:
        criteria_by_area[c.area_id].append(c)

    candidates = (await db.execute(
        select(Candidate).where(
            Candidate.project_id == project_id,
            Candidate.id != reference.id,
        )
    )).scalars().all()
    if not candidates:
        raise ConsensusError("no candidates to rank")

    all_ids = [c.id for c in candidates] + [reference.id]
    chars = (await db.execute(
        select(CandidateCharacteristic).where(
            CandidateCharacteristic.candidate_id.in_(all_ids)
        )
    )).scalars().all()

    values: dict[tuple[uuid.UUID, uuid.UUID], float] = {}
    for ch in chars:
        if ch.value_numeric is not None:
            values[(ch.candidate_id, ch.criterion_id)] = ch.value_numeric

    # Resolve weights — None = all 1.0; else use provided; missing = 0.
    if weights is None:
        resolved = {a.id: 1.0 for a in areas}
    else:
        resolved = {a.id: float(weights.get(str(a.id), 0.0)) for a in areas}

    total_weight = sum(resolved.values())
    if total_weight <= 0:
        raise ConsensusError("total weight must be positive")

    # Min-max ranges per criterion, across all candidates + reference.
    ranges: dict[uuid.UUID, tuple[float, float]] = {}
    for crit in criteria:
        vals = [values[(cid, crit.id)] for cid in all_ids if (cid, crit.id) in values]
        if len(vals) >= 2:
            ranges[crit.id] = (min(vals), max(vals))
        elif len(vals) == 1:
            ranges[crit.id] = (vals[0], vals[0])

    def scaled(cid, crit_id):
        if (cid, crit_id) not in values or crit_id not in ranges:
            return None
        mn, mx = ranges[crit_id]
        if mx == mn:
            return 0.5
        return (values[(cid, crit_id)] - mn) / (mx - mn)

    results = []
    for cand in candidates:
        per_area = {}
        per_criterion = {}
        for area in areas:
            diffs = []
            for crit in criteria_by_area.get(area.id, []):
                ref_s = scaled(reference.id, crit.id)
                cand_s = scaled(cand.id, crit.id)
                if ref_s is None or cand_s is None:
                    continue
                d = cand_s - ref_s
                diffs.append(d * d)
                per_criterion[str(crit.id)] = {
                    "criterion": crit.name,
                    "candidate_value": values[(cand.id, crit.id)],
                    "reference_value": values[(reference.id, crit.id)],
                    "scaled_candidate": round(cand_s, 4),
                    "scaled_reference": round(ref_s, 4),
                    "unit": crit.unit,
                }
            if not diffs:
                per_area[str(area.id)] = {
                    "area": area.name,
                    "score": None,
                    "criteria_used": 0,
                }
                continue
            distance = math.sqrt(sum(diffs))
            max_distance = math.sqrt(len(diffs))  # dims are in [0,1] so max diff per dim = 1
            score = 1.0 - (distance / max_distance) if max_distance > 0 else 1.0
            per_area[str(area.id)] = {
                "area": area.name,
                "score": round(score, 4),
                "criteria_used": len(diffs),
            }

        # Weighted average across areas that had data.
        wsum = 0.0
        wtotal = 0.0
        for aid_str, data in per_area.items():
            if data["score"] is None:
                continue
            w = resolved[uuid.UUID(aid_str)]
            wsum += data["score"] * w
            wtotal += w
        total = round(wsum / wtotal, 4) if wtotal > 0 else None

        results.append({
            "candidate_id": str(cand.id),
            "candidate_name": cand.name,
            "country": cand.country,
            "total": total,
            "per_area": per_area,
            "per_criterion": per_criterion,
        })

    # Sort: known totals first, descending; unknown last.
    results.sort(key=lambda r: (r["total"] is None, -(r["total"] or 0.0)))

    return {
        "project_id": str(project_id),
        "target": project.target.value,
        "reference_candidate_id": str(reference.id),
        "reference_candidate_name": reference.name,
        "weights": {str(k): v for k, v in resolved.items()},
        "total_weight": total_weight,
        "results": results,
    }