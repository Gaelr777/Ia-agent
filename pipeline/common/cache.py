"""Caché genérico respaldado por la tabla `api_cache` de Supabase.

Evita repetir llamadas a INEGI o a portales de vacantes dentro de la
ventana de TTL. No es un caché en memoria: vive en Supabase para que
persista entre corridas distintas de GitHub Actions (cada corrida es un
runner nuevo, sin disco compartido).
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pipeline.common.supabase_client import get_client


def make_key(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(cache_key: str) -> Optional[Any]:
    client = get_client()
    now = datetime.now(timezone.utc).isoformat()
    resp = (
        client.table("api_cache")
        .select("response_json, expires_at")
        .eq("cache_key", cache_key)
        .gte("expires_at", now)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["response_json"]
    return None


def set(cache_key: str, value: Any, ttl: timedelta) -> None:
    client = get_client()
    now = datetime.now(timezone.utc)
    client.table("api_cache").upsert(
        {
            "cache_key": cache_key,
            "response_json": json.loads(json.dumps(value)),  # normaliza a JSON-safe
            "fetched_at": now.isoformat(),
            "expires_at": (now + ttl).isoformat(),
        }
    ).execute()
