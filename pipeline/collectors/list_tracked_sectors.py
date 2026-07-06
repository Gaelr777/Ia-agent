"""Imprime en stdout un JSON array con los códigos SCIAN marcados como
`is_tracked=true`, para alimentar la matrix de monthly-collection.yml.

Uso: python -m pipeline.collectors.list_tracked_sectors
"""
import json

from pipeline.common.supabase_client import get_client


def main() -> None:
    client = get_client()
    rows = client.table("sectors").select("scian_code").eq("is_tracked", True).execute().data
    print(json.dumps([row["scian_code"] for row in rows]))


if __name__ == "__main__":
    main()
