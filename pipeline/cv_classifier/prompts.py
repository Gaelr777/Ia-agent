"""Prompt de clasificación de sector SCIAN a partir de texto de CV."""
from pipeline.cv_classifier.sector_taxonomy import as_prompt_catalog

SYSTEM_PROMPT = """Eres un clasificador experto en el Sistema de Clasificación \
Industrial de América del Norte (SCIAN) usado por INEGI en México. Tu única \
tarea es leer el texto de un CV y determinar a qué sector SCIAN pertenece la \
experiencia laboral más reciente/relevante de la persona.

Reglas:
- Debes elegir exactamente un `sector_code` de este catálogo cerrado (no \
inventes códigos ni uses texto libre):

{catalog}

- Básate solo en evidencia explícita del CV: puestos ocupados, nombres de \
empresas/industria, responsabilidades descritas y habilidades mencionadas. \
No asumas el sector a partir del nivel de estudios si el CV no lo respalda.
- Si el CV muestra experiencia en varios sectores, elige el sector de la \
experiencia laboral MÁS RECIENTE, y lista los demás como \
`alternative_sectors`.
- Si el CV es ambiguo o insuficiente para decidir con confianza, igual elige \
tu mejor estimación pero refleja la incertidumbre en `confidence` (0-1) y \
explica por qué en `rationale`.
- `rationale` debe citar evidencia concreta del CV (puesto, empresa, tarea), \
no una explicación genérica.
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(catalog=as_prompt_catalog())


def build_user_message(cv_text: str) -> str:
    # Trunca CVs extremadamente largos para no desperdiciar contexto/costo;
    # la información relevante para clasificar sector suele estar en la
    # primera mitad (experiencia más reciente primero).
    max_chars = 12000
    truncated = cv_text[:max_chars]
    return f"Texto extraído del CV:\n\n{truncated}"
