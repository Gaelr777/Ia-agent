"""Clasificación de sector SCIAN a partir de texto de CV, usando la API de
Claude (Messages API) con tool use forzado para obtener salida estructurada
en vez de texto libre.
"""
from typing import TypedDict

import anthropic

from pipeline.common import config
from pipeline.cv_classifier.prompts import build_system_prompt, build_user_message
from pipeline.cv_classifier.sector_taxonomy import valid_codes

_TOOL_NAME = "clasificar_sector"

_TOOL_SCHEMA = {
    "name": _TOOL_NAME,
    "description": "Registra la clasificación de sector SCIAN detectada en el CV.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sector_code": {
                "type": "string",
                "description": "Código SCIAN elegido, tal cual aparece en el catálogo (ej. '31-33').",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confianza de la clasificación principal.",
            },
            "rationale": {
                "type": "string",
                "description": "Evidencia concreta del CV que sustenta la elección.",
            },
            "alternative_sectors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sector_code": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["sector_code", "confidence"],
                },
                "description": "Otros sectores candidatos con evidencia en el CV, si los hay.",
            },
        },
        "required": ["sector_code", "confidence", "rationale"],
    },
}


class SectorClassification(TypedDict):
    sector_code: str
    confidence: float
    rationale: str
    alternative_sectors: list[dict]
    raw_model_output: dict
    model_used: str


class InvalidClassification(ValueError):
    pass


def classify_cv_text(cv_text: str) -> SectorClassification:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    model = config.claude_model()

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=build_system_prompt(),
        messages=[{"role": "user", "content": build_user_message(cv_text)}],
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"), None
    )
    if tool_use_block is None:
        raise InvalidClassification("El modelo no devolvió una llamada a la herramienta.")

    result = tool_use_block.input
    sector_code = result.get("sector_code")
    if sector_code not in valid_codes():
        raise InvalidClassification(
            f"El modelo devolvió un sector_code fuera del catálogo: {sector_code!r}"
        )

    return SectorClassification(
        sector_code=sector_code,
        confidence=float(result["confidence"]),
        rationale=result["rationale"],
        alternative_sectors=result.get("alternative_sectors", []),
        raw_model_output=result,
        model_used=model,
    )
