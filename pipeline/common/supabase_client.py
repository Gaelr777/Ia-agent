"""Cliente Supabase compartido, autenticado con la service_role key.

Usa la service_role key (no la anon key) porque estos scripts corren en
GitHub Actions, no en el navegador del usuario, y necesitan saltarse RLS
para escribir en las tablas del pipeline.
"""
from functools import lru_cache

from supabase import Client, create_client

from pipeline.common import config


@lru_cache(maxsize=1)
def get_client() -> Client:
    return create_client(config.supabase_url(), config.supabase_service_role_key())
