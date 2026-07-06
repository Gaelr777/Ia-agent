"""Entry point para el paso 1 del pipeline (CV -> sector).

Dos modos:
  --file RUTA     Prueba local: extrae texto, clasifica, imprime el
                   resultado. No toca Supabase. Útil para probar el prompt.
  --cv-id UUID     Modo producción (usado por process-cv.yml): descarga el
                   CV desde Supabase Storage, clasifica, y persiste el
                   resultado en `cv_sector_classifications`, actualizando
                   `cvs.status`.
"""
import argparse
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.common.supabase_client import get_client
from pipeline.cv_classifier.classify_sector import (
    InvalidClassification,
    classify_cv_text,
)
from pipeline.cv_classifier.extract_text import extract_text

STORAGE_BUCKET = "cvs"


def run_local_file(file_path: str) -> None:
    text = extract_text(file_path)
    if not text.strip():
        print("No se pudo extraer texto del archivo (¿PDF escaneado sin OCR?).")
        sys.exit(1)
    result = classify_cv_text(text)
    print(f"sector_code:  {result['sector_code']}")
    print(f"confidence:   {result['confidence']}")
    print(f"rationale:    {result['rationale']}")
    if result["alternative_sectors"]:
        print(f"alternativas: {result['alternative_sectors']}")


def run_cv_id(cv_id: str) -> None:
    client = get_client()
    cv_row = (
        client.table("cvs").select("*").eq("id", cv_id).single().execute().data
    )
    if cv_row is None:
        raise SystemExit(f"No existe un CV con id={cv_id}")

    client.table("cvs").update({"status": "processing"}).eq("id", cv_id).execute()

    try:
        suffix = Path(cv_row["file_name"]).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            file_bytes = client.storage.from_(STORAGE_BUCKET).download(
                cv_row["storage_path"]
            )
            tmp.write(file_bytes)
            tmp.flush()

            text = extract_text(tmp.name)
            if not text.strip():
                raise InvalidClassification(
                    "No se pudo extraer texto del archivo (¿PDF escaneado sin OCR?)."
                )
            result = classify_cv_text(text)

        client.table("cv_sector_classifications").upsert(
            {
                "cv_id": cv_id,
                "scian_code": result["sector_code"],
                "confidence": result["confidence"],
                "rationale": result["rationale"],
                "alternative_codes": result["alternative_sectors"],
                "model_used": result["model_used"],
                "raw_model_output": result["raw_model_output"],
            },
            on_conflict="cv_id",
        ).execute()

        client.table("cvs").update(
            {"status": "classified", "processed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", cv_id).execute()
        print(f"CV {cv_id} clasificado como sector {result['sector_code']}")

    except Exception as exc:
        client.table("cvs").update(
            {
                "status": "error",
                "error_message": str(exc),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", cv_id).execute()
        raise


def run_pending() -> None:
    """Procesa todos los CVs con status='pending'. Pensado para correr en un
    schedule corto (ver .github/workflows/process-cv.yml) mientras no
    tengas configurado el webhook de Supabase -> GitHub."""
    client = get_client()
    pending = client.table("cvs").select("id").eq("status", "pending").execute().data
    if not pending:
        print("No hay CVs pendientes.")
        return
    for row in pending:
        try:
            run_cv_id(row["id"])
        except Exception as exc:  # noqa: BLE001 - se registra y se sigue con el resto
            print(f"Error procesando CV {row['id']}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Ruta local a un CV (PDF/DOCX) para probar")
    group.add_argument("--cv-id", help="ID de la fila en la tabla `cvs` a procesar")
    group.add_argument(
        "--pending", action="store_true", help="Procesa todos los CVs con status='pending'"
    )
    args = parser.parse_args()

    if args.file:
        run_local_file(args.file)
    elif args.cv_id:
        run_cv_id(args.cv_id)
    else:
        run_pending()


if __name__ == "__main__":
    main()
