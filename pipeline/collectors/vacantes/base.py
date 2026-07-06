"""Utilidades compartidas por los colectores de vacantes: sesión HTTP con
rate limiting + verificación de robots.txt, tipo común de vacante, y helper
de persistencia en Supabase.

Cada colector concreto (empleo_gob.py, occ_mundial.py, ...) implementa su
propio `search(scian_code, keywords) -> list[JobPosting]` y usa
`RateLimitedSession` para las requests HTTP.
"""
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlparse

import requests

from pipeline.common import config
from pipeline.common.supabase_client import get_client

USER_AGENT = (
    "MonitorMercadoLaboralMX/1.0 (+bot de investigación de mercado laboral; "
    "contacto: configura CONTACT_EMAIL en el workflow)"
)


@dataclass
class JobPosting:
    external_id: str
    title: str
    company: str | None
    location: str | None
    description_raw: str
    description_url: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    posted_at: date | None = None


class RobotsDisallowed(RuntimeError):
    pass


class RateLimitedSession:
    """Envoltura sobre requests.Session que respeta robots.txt y aplica un
    delay mínimo entre requests al mismo host."""

    def __init__(self, delay_seconds: float | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.delay_seconds = delay_seconds or config.request_delay_seconds()
        self._last_request_at: dict[str, float] = {}
        self._robots_parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _robots_parser_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        host = urlparse(url).netloc
        if host not in self._robots_parsers:
            parser = urllib.robotparser.RobotFileParser()
            robots_url = urljoin(f"https://{host}", "/robots.txt")
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception:
                pass  # si no se puede leer robots.txt, se procede con cautela pero no se bloquea
            self._robots_parsers[host] = parser
        return self._robots_parsers[host]

    def get(self, url: str, **kwargs) -> requests.Response:
        if not self._robots_parser_for(url).can_fetch(USER_AGENT, url):
            raise RobotsDisallowed(f"robots.txt prohíbe acceder a {url}")

        host = urlparse(url).netloc
        elapsed = time.monotonic() - self._last_request_at.get(host, 0)
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

        response = self.session.get(url, timeout=30, **kwargs)
        self._last_request_at[host] = time.monotonic()
        return response


def persist_postings(
    source_name: str, scian_code: str, postings: list[JobPosting]
) -> int:
    client = get_client()
    source_row = (
        client.table("job_sources").select("id, enabled").eq("name", source_name).single().execute().data
    )
    if source_row is None:
        raise RuntimeError(f"Fuente desconocida en job_sources: {source_name}")
    if not source_row["enabled"]:
        print(f"Fuente {source_name} está deshabilitada (job_sources.enabled=false); se omite.")
        return 0

    snapshot_month = datetime.now(timezone.utc).date().replace(day=1)
    count = 0
    for posting in postings:
        client.table("job_postings").upsert(
            {
                "source_id": source_row["id"],
                "external_id": posting.external_id,
                "scian_code": scian_code,
                "title": posting.title,
                "company": posting.company,
                "location": posting.location,
                "salary_min": posting.salary_min,
                "salary_max": posting.salary_max,
                "posted_at": posting.posted_at.isoformat() if posting.posted_at else None,
                "description_url": posting.description_url,
                "description_raw": posting.description_raw,
                "snapshot_month": snapshot_month.isoformat(),
            },
            on_conflict="source_id,external_id,snapshot_month",
        ).execute()
        count += 1
    return count
