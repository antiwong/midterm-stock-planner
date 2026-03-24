from src.api.db import cached_response
"""Runs router — list and detail for analysis runs (shared by multiple pages)."""

from fastapi import APIRouter

from src.data.shared_db import load_runs_from_db, load_run_by_id

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
@cached_response(ttl=600)
def list_runs():
    """List all analysis runs."""
    runs = load_runs_from_db()
    return {"runs": runs, "count": len(runs)}


@router.get("/{run_id}")
@cached_response(ttl=600)
def get_run(run_id: str):
    """Get a single run by ID."""
    run = load_run_by_id(run_id)
    if run is None:
        return {"error": "Run not found"}
    return run
