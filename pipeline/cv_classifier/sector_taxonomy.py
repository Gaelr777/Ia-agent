"""Carga el catálogo SCIAN (data/scian_sectors.json) usado para acotar al
modelo las categorías válidas de salida."""
import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "scian_sectors.json"


class Sector(TypedDict):
    code: str
    name: str


@lru_cache(maxsize=1)
def load_sectors() -> list[Sector]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def valid_codes() -> set[str]:
    return {s["code"] for s in load_sectors()}


def as_prompt_catalog() -> str:
    """Formatea el catálogo como lista 'code — name' para incrustar en el prompt."""
    return "\n".join(f"{s['code']} — {s['name']}" for s in load_sectors())
