# Guía de setup — obtener credenciales desde cero

Como todavía no tienes ninguna credencial, aquí está el orden recomendado.
Ninguno de estos pasos lo puedo hacer yo por ti (requieren tu cuenta/aceptar
ToS/pagar en su caso), pero el código ya está listo para consumirlas en
cuanto las tengas.

## 1. Supabase (gratis para empezar)

1. Crea cuenta en https://supabase.com y un nuevo proyecto (elige región
   más cercana a tus usuarios, ej. `us-east-1`).
2. En **Project Settings → API** copia:
   - `Project URL` → variable `SUPABASE_URL`
   - `service_role` key (¡no la `anon` key para el pipeline, la `service_role`
     tiene permisos para escribir sin RLS!) → variable `SUPABASE_SERVICE_ROLE_KEY`
   - Guarda también la `anon` key para el frontend (esa sí respeta RLS).
3. Corre la migración de este repo:
   `supabase/migrations/0001_init.sql` (puedes pegarlo directo en el
   **SQL Editor** del dashboard de Supabase, o usar la Supabase CLI:
   `supabase db push`).
4. Crea un bucket de **Storage** llamado `cvs` (privado) para los archivos
   subidos.
5. (Opcional, para disparo casi instantáneo) en **Database → Webhooks**
   crea uno sobre `INSERT` en la tabla `cvs` que llame a un Edge Function o
   a un endpoint que dispare `repository_dispatch` en GitHub. Si no lo
   configuras ahora, el workflow `process-cv.yml` igual funciona vía
   `workflow_dispatch` manual o polling (ver `docs/ARCHITECTURE.md`).

## 2. Token de la API de Indicadores de INEGI (gratis, inmediato)

1. Ve a https://www.inegi.org.mx/servicios/api_indicadores.html
2. Sigue el enlace de "generar token" (formulario corto, sin costo).
3. Guarda el token → variable `INEGI_API_TOKEN`.
4. **Importante**: los IDs numéricos de indicador (ej. la tasa de
   desocupación nacional, o los indicadores de EMIM por subsector
   manufacturero) hay que localizarlos tú mismo la primera vez con el
   "Constructor de Consultas" en https://www.inegi.org.mx/app/indicadores/ —
   INEGI no tiene una API de búsqueda por palabra clave para su catálogo.
   `pipeline/collectors/inegi/series_config.yaml` trae varios IDs
   pre-cargados (los más citados en la documentación pública de INEGI/ENOE)
   marcados como `verified: false` donde no pude confirmar el ID con 100%
   de certeza desde este entorno (no tengo acceso de red saliente a
   inegi.org.mx desde aquí). Antes de confiar en producción en cualquier
   serie, corre:

   ```bash
   python -m pipeline.collectors.inegi.verify_series --indicator-id 444612
   ```

   Este script llama al endpoint de metadatos y te imprime el nombre real
   del indicador para que confirmes que corresponde a lo que esperas.

## 3. API key de Anthropic (Claude)

1. Ve a https://console.anthropic.com y crea una cuenta / organización.
2. **API Keys → Create Key** → variable `ANTHROPIC_API_KEY`.
3. El pipeline usa el modelo `claude-sonnet-5` por defecto (parametrizable
   vía `CLAUDE_MODEL`). Para el paso de clasificación de sector y extracción
   de skills, es más que suficiente; si el volumen de vacantes crece mucho
   y el costo importa, puedes bajar a un modelo más económico cambiando esa
   variable.

## 4. Configurar GitHub Secrets

En el repo → **Settings → Secrets and variables → Actions**, agrega:

| Secret                        | De dónde sale               |
|--------------------------------|------------------------------|
| `SUPABASE_URL`                 | Paso 1                       |
| `SUPABASE_SERVICE_ROLE_KEY`    | Paso 1                       |
| `INEGI_API_TOKEN`              | Paso 2                       |
| `ANTHROPIC_API_KEY`            | Paso 3                       |
| `GH_DISPATCH_TOKEN` (opcional) | Solo si configuras el webhook de Supabase → GitHub |

## 5. Primer corrida de prueba (local, antes de confiar en Actions)

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
export INEGI_API_TOKEN=...
export ANTHROPIC_API_KEY=...

# 1. Clasificar un CV de prueba
python -m pipeline.cv_classifier.cli --file /ruta/a/cv_de_prueba.pdf

# 2. Recolectar datos INEGI + vacantes para el sector piloto (Manufactura = 31-33)
python -m pipeline.collectors.inegi.collect --sector 31-33
python -m pipeline.collectors.vacantes.collect --sector 31-33

# 3. Extraer skills y generar reporte del mes
python -m pipeline.analysis.skills_extraction --sector 31-33
python -m pipeline.analysis.generate_report --sector 31-33 --period $(date +%Y-%m)
```

Cuando esto corra limpio en local, activa los workflows en
`.github/workflows/` (ya están listos, solo necesitan los secrets del
paso 4).
