"""Diagnóstico puntual: prueba si ciertos hosts bloquean peticiones desde
este runner (ej. por rango de IP de datacenter/nube). No es parte del
pipeline normal — solo para depurar disponibilidad de fuentes antes de
invertir en selectores/scraper completos.

Uso: python -m pipeline.collectors.vacantes.diagnose_hosts
"""
import requests

HOSTS = [
    "https://www.empleo.gob.mx/",
    "https://www.occ.com.mx/",
    "https://www.computrabajo.com.mx/",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def main() -> None:
    for url in HOSTS:
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
            print(f"{url} -> HTTP {response.status_code} ({len(response.text)} bytes)")
        except Exception as exc:
            print(f"{url} -> ERROR: {exc}")


if __name__ == "__main__":
    main()
