"""Bitácora de corridas de recolección (tabla `collection_runs`).

Uso:
    with CollectionRun("inegi", scian_code="31-33") as run:
        ... hacer el trabajo ...
        run.records_collected = 42
"""
from datetime import datetime, timezone

from pipeline.common.supabase_client import get_client


class CollectionRun:
    def __init__(self, source: str, scian_code: str | None = None):
        self.source = source
        self.scian_code = scian_code
        self.records_collected = 0
        self._row_id = None

    def __enter__(self) -> "CollectionRun":
        client = get_client()
        resp = (
            client.table("collection_runs")
            .insert(
                {
                    "source": self.source,
                    "scian_code": self.scian_code,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "running",
                }
            )
            .execute()
        )
        self._row_id = resp.data[0]["id"]
        return self

    def __exit__(self, exc_type, exc_value, _traceback) -> None:
        client = get_client()
        client.table("collection_runs").update(
            {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "error" if exc_type else "success",
                "records_collected": self.records_collected,
                "error_message": str(exc_value) if exc_value else None,
            }
        ).eq("id", self._row_id).execute()
        # No suprimimos la excepción: que el workflow de Actions falle visible.
