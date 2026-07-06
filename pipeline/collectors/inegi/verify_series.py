"""Ayuda a confirmar que un indicator_id de INEGI trae los datos esperados
antes de darlo de alta en series_config.yaml.

Uso:
    python -m pipeline.collectors.inegi.verify_series --indicator-id 444612
"""
import argparse
import json

from pipeline.collectors.inegi.client import fetch_indicators


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indicator-id", required=True)
    parser.add_argument("--area", default="00", help="Área geográfica (00 = nacional)")
    args = parser.parse_args()

    data = fetch_indicators([args.indicator_id], area_geografica=args.area, use_cache=False)
    print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
    print(
        "\nRevisa arriba las observaciones (OBSERVATIONS) y confirma en "
        "https://www.inegi.org.mx/app/indicadores/ que el ID corresponde al "
        "indicador que crees que es, antes de usarlo en series_config.yaml."
    )


if __name__ == "__main__":
    main()
