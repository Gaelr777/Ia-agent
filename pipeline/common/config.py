"""Configuración centralizada leída de variables de entorno.

Todos los scripts del pipeline importan de aquí en vez de leer `os.environ`
directamente, para que falle rápido y claro si falta una variable.
"""
import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. Revisa docs/SETUP.md."
        )
    return value


def supabase_url() -> str:
    return _require("SUPABASE_URL")


def supabase_service_role_key() -> str:
    return _require("SUPABASE_SERVICE_ROLE_KEY")


def inegi_api_token() -> str:
    return _require("INEGI_API_TOKEN")


def anthropic_api_key() -> str:
    return _require("ANTHROPIC_API_KEY")


def claude_model() -> str:
    return os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")


def request_delay_seconds() -> float:
    return float(os.environ.get("REQUEST_DELAY_SECONDS", "4"))


def cache_ttl_days_inegi() -> int:
    return int(os.environ.get("CACHE_TTL_DAYS_INEGI", "25"))


def cache_ttl_hours_vacantes() -> int:
    return int(os.environ.get("CACHE_TTL_HOURS_VACANTES", "12"))
