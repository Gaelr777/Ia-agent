"""Extracción de hard/soft skills de las vacantes recolectadas, usando la
API de Claude (Messages API) con tool use forzado.

Procesa solo `job_postings` del sector/mes que aún no tienen filas en
`job_posting_skills`, para no re-procesar (y re-pagar) vacantes ya vistas.
"""
import argparse
import re
from datetime import datetime, timezone

import anthropic

from pipeline.common import config
from pipeline.common.supabase_client import get_client

_TOOL_NAME = "registrar_skills"

_TOOL_SCHEMA = {
    "name": _TOOL_NAME,
    "description": "Registra las habilidades técnicas y blandas detectadas en una vacante.",
    "input_schema": {
        "type": "object",
        "properties": {
            "hard_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Habilidades técnicas explícitas (herramientas, lenguajes, certificaciones, maquinaria, normas). Nombres cortos y normalizados (ej. 'Python', 'ISO 9001', 'SAP').",
            },
            "soft_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Habilidades blandas explícitas o fuertemente implícitas (ej. 'trabajo en equipo', 'comunicación efectiva').",
            },
        },
        "required": ["hard_skills", "soft_skills"],
    },
}

SYSTEM_PROMPT = """Eres un analista de mercado laboral. Lee la descripción de \
una vacante de empleo en México y extrae las habilidades técnicas (hard \
skills) y habilidades blandas (soft skills) que el empleador pide o valora.

Reglas:
- Solo incluye habilidades con respaldo explícito en el texto (no inventes).
- Normaliza variantes obvias al mismo término (ej. "Excel avanzado" y \
"manejo de Excel" -> "Excel"), pero no fusiones habilidades distintas.
- Usa nombres cortos, en español salvo que la habilidad sea un nombre \
propio/tecnología (ej. "Python", "SAP", "AutoCAD").
- Si la vacante no menciona ninguna habilidad de un tipo, devuelve una \
lista vacía para ese tipo — no la rellenes con inferencias débiles."""


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _get_or_create_skill(client, name: str, skill_type: str) -> str:
    normalized = _normalize(name)
    existing = (
        client.table("skills_catalog")
        .select("id")
        .eq("normalized_name", normalized)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return existing[0]["id"]

    row = (
        client.table("skills_catalog")
        .insert(
            {
                "normalized_name": normalized,
                "display_name": name.strip(),
                "skill_type": skill_type,
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    return row.data[0]["id"]


def extract_skills_from_text(description: str) -> dict:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    response = client.messages.create(
        model=config.claude_model(),
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Descripción de la vacante:\n\n{description[:6000]}"}],
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )
    tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use_block is None:
        return {"hard_skills": [], "soft_skills": []}
    return tool_use_block.input


def _postings_pending_extraction(client, sector: str, snapshot_month: str) -> list[dict]:
    postings = (
        client.table("job_postings")
        .select("id, description_raw")
        .eq("scian_code", sector)
        .eq("snapshot_month", snapshot_month)
        .execute()
        .data
    )
    already_processed = {
        row["job_posting_id"]
        for row in client.table("job_posting_skills")
        .select("job_posting_id")
        .in_("job_posting_id", [p["id"] for p in postings] or ["00000000-0000-0000-0000-000000000000"])
        .execute()
        .data
    }
    return [p for p in postings if p["id"] not in already_processed and p["description_raw"]]


def run(sector: str, snapshot_month: str) -> int:
    client = get_client()
    pending = _postings_pending_extraction(client, sector, snapshot_month)
    processed = 0

    for posting in pending:
        result = extract_skills_from_text(posting["description_raw"])
        for skill_name in result.get("hard_skills", []):
            skill_id = _get_or_create_skill(client, skill_name, "hard")
            client.table("job_posting_skills").upsert(
                {"job_posting_id": posting["id"], "skill_id": skill_id},
                on_conflict="job_posting_id,skill_id",
            ).execute()
        for skill_name in result.get("soft_skills", []):
            skill_id = _get_or_create_skill(client, skill_name, "soft")
            client.table("job_posting_skills").upsert(
                {"job_posting_id": posting["id"], "skill_id": skill_id},
                on_conflict="job_posting_id,skill_id",
            ).execute()
        processed += 1

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", required=True)
    parser.add_argument(
        "--snapshot-month",
        default=datetime.now(timezone.utc).date().replace(day=1).isoformat(),
        help="Primer día del mes a procesar, formato YYYY-MM-01 (default: mes actual)",
    )
    args = parser.parse_args()

    count = run(args.sector, args.snapshot_month)
    print(f"Vacantes procesadas para skills: {count}")


if __name__ == "__main__":
    main()
