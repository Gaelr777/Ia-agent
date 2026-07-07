"""Cliente para la API de Indicadores (Banco de Indicadores / BISE) de INEGI.

Referencia: https://www.inegi.org.mx/servicios/api_indicadores.html

IMPORTANTE — verificación pendiente: el patrón de URL de abajo es el
documentado públicamente y usado por librerías de terceros (ej. INEGIpy),
pero este entorno de desarrollo no tiene salida de red hacia inegi.org.mx,
así que no pude probarlo en vivo end-to-end. Antes de confiar en producción,
corre `verify_series.py` con tu token real y confirma que la respuesta trae
los valores esperados.
"""
import requests

from pipeline.common import cache, config
from datetime import timedelta

BASE_URL = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml"
NATIONAL_AREA = "00"  # área geográfica nacional en el catálogo de INEGI (sin verificar en vivo, ver docstring del módulo)


class InegiApiError(RuntimeError):
    pass


def _build_indicator_url(
    indicator_ids: list[str],
    area_geografica: str,
    idioma: str,
    recientes: bool,
    token: str,
) -> str:
    ids = ",".join(indicator_ids)
    recientes_str = "true" if recientes else "false"
    return (
        f"{BASE_URL}/INDICATOR/{ids}/{idioma}/{area_geografica}/"
        f"{recientes_str}/BISE/2.0/{token}?type=json"
    )


def fetch_indicators(
    indicator_ids: list[str],
    area_geografica: str = NATIONAL_AREA,
    idioma: str = "es",
    recientes: bool = True,
    use_cache: bool = True,
) -> dict:
    """Trae uno o más indicadores. Devuelve el JSON crudo de INEGI (una lista
    `Series`, cada una con `INDICADOR` y `OBSERVATIONS`)."""
    cache_key = cache.make_key("inegi", *sorted(indicator_ids), area_geografica, idioma, recientes)
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    token = config.inegi_api_token()
    url = _build_indicator_url(indicator_ids, area_geografica, idioma, recientes, token)
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise InegiApiError(
            f"INEGI respondió {response.status_code} para indicadores {indicator_ids}: "
            f"{response.text[:500]}"
        )
    data = response.json()

    if use_cache:
        cache.set(cache_key, data, ttl=timedelta(days=config.cache_ttl_days_inegi()))
    return data


def parse_observations(raw_response: dict) -> list[dict]:
    """Aplana la respuesta cruda a una lista de
    {indicator_id, period (YYYY-MM-DD), value} lista para insertar en
    `inegi_snapshots`."""
    rows = []
    for serie in raw_response.get("Series", []):
        indicator_id = serie.get("INDICADOR")
        for obs in serie.get("OBSERVATIONS", []):
            period = _parse_time_period(obs.get("TIME_PERIOD", ""))
            value = obs.get("OBS_VALUE")
            if period is None or value in (None, "", "N/E"):
                continue
            rows.append(
                {
                    "indicator_id": indicator_id,
                    "period": period,
                    "value": float(value),
                }
            )
    return rows


def _parse_time_period(time_period: str) -> str | None:
    """INEGI usa formatos como '2024/01' (mensual) o '2024/01' para
    trimestres codificados como mes de inicio. Normalizamos a
    'YYYY-MM-01'."""
    if not time_period or "/" not in time_period:
        return None
    year, period = time_period.split("/", 1)
    period = period.zfill(2)[:2]
    try:
        return f"{int(year):04d}-{int(period):02d}-01"
    except ValueError:
        return None
