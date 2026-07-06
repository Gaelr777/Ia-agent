# Arquitectura — Monitor de Mercado Laboral MX

## Principios de diseño

- **Sin frameworks de agentes.** Cada paso es un script Python invocado por GitHub
  Actions. No hay un "agente autónomo" que decida qué hacer: el flujo de control
  vive en los workflows YAML, y cada script hace una cosa y termina.
- **Dos pipelines independientes** que se comunican solo a través de Supabase:
  1. **CV → Sector** (evento: usuario sube un CV).
  2. **Sector → Datos → Reporte** (evento: cron mensual, o el sector recién
     detectado en el paso 1).

  Esto cumple el requisito de modularidad: el paso 2 no sabe ni le importa de
  dónde salió el `scian_code` que recibe — puede venir de un CV o de que un
  admin lo dispare a mano para un sector nuevo.

## Diagrama de módulos

```
┌─────────────────────┐      sube CV (PDF/DOCX)      ┌──────────────────────┐
│  Frontend (upload)  │ ───────────────────────────▶ │  Supabase Storage    │
└─────────────────────┘                               │  bucket: cvs         │
           │                                           └──────────┬───────────┘
           │ INSERT en tabla `cvs` (status=pending)                │
           ▼                                                       │
┌─────────────────────────────────────────────────────────────────┴──────┐
│  Supabase Postgres                                                     │
│  trigger/webhook (Database Webhook) ──▶ repository_dispatch a GH       │
└──────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│ GitHub Actions: process-cv.yml                           │
│  1. descarga CV de Storage                               │
│  2. extract_text.py       (PDF/DOCX -> texto plano)      │
│  3. classify_sector.py    (Claude Messages API)          │
│  4. INSERT en cv_sector_classifications                  │
│  5. (opcional) dispara monthly-collection.yml con        │
│     scian_code recién detectado si no hay datos frescos  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ GitHub Actions: monthly-collection.yml (cron 1º de mes,  │
│ + workflow_dispatch manual con input scian_code)         │
│                                                            │
│  Para cada sector activo (tabla `sectors` con              │
│  is_tracked=true, o el sector pasado como input):          │
│                                                            │
│  1. collectors/inegi/collect.py                           │
│     -> INEGI API Indicadores (ENOE, EMIM, IGAE...)         │
│     -> upsert en inegi_snapshots (con caché en api_cache)  │
│                                                            │
│  2. collectors/vacantes/collect.py                        │
│     -> Portal del Empleo (fuente primaria, gob.mx)         │
│     -> [opcional/flag] OCC Mundial, Computrabajo           │
│     -> upsert en job_postings                              │
│                                                            │
│  3. analysis/skills_extraction.py                          │
│     -> Claude Messages API sobre cada job_posting nuevo    │
│     -> INSERT en job_posting_skills + skills_catalog        │
│                                                            │
│  4. analysis/trends.py                                     │
│     -> compara mes actual vs. mes anterior por sector       │
│                                                            │
│  5. analysis/generate_report.py                            │
│     -> arma report_json + summary_md                        │
│     -> upsert en monthly_sector_reports                     │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Frontend (dashboard)│  lee directo de Supabase (monthly_sector_reports,
└─────────────────────┘  inegi_snapshots, job_posting_skills) vía supabase-js.
```

## Por qué así (y no con CrewAI/LangGraph/AutoGen)

Todo el "razonamiento agéntico" real en este sistema son dos llamadas puntuales
a la API de Claude con un prompt bien acotado y salida estructurada (tool use):

1. Clasificar sector desde texto de CV → una llamada, una respuesta JSON.
2. Extraer hard/soft skills de una vacante → una llamada por vacante (o batch),
   una respuesta JSON.

No hay necesidad de que el modelo decida qué herramienta usar, mantenga estado
conversacional entre pasos, ni orqueste sub-agentes. Un framework de agentes
añadiría una capa de indirección (grafo de estados, memoria, colas de
mensajes) para resolver un problema que ya resuelven bien: (a) un script
Python síncrono y (b) GitHub Actions como orquestador de cron/eventos. Esto
es más barato, más fácil de debuggear (logs de Actions vs. traces de agente),
y más fácil de testear (cada función es pura y unit-testeable).

Si en el futuro necesitas que el sistema decida dinámicamente *qué fuentes
consultar* según el sector (ej. "para Tecnología, prioriza LinkedIn; para
Manufactura, prioriza EMIM"), eso sigue siendo una tabla de configuración
(`sector_source_priority`), no un agente.

## Disparo del pipeline 1 (CV → Sector)

Dos formas de disparar `process-cv.yml`, de más a menos recomendada:

1. **Supabase Database Webhook** sobre `INSERT` en `cvs` → llama a un Edge
   Function pequeño (o directo) que hace `POST` a
   `https://api.github.com/repos/<owner>/<repo>/dispatches` con
   `event_type: cv_uploaded` y `client_payload: {cv_id}`. Requiere un PAT de
   GitHub guardado como secret en Supabase.
2. **Manual / polling**: si no quieres configurar el webhook todavía, un
   `workflow_dispatch` con input `cv_id`, y el frontend simplemente le dice al
   usuario "tu CV se está procesando, vuelve en 1-2 min" mientras un
   `schedule` corto (cada 5 min) revisa si hay CVs `status=pending`. Menos
   elegante pero cero configuración adicional fuera de GitHub.

Empieza con la opción 2 (ya viene lista en `process-cv.yml`), migra a la 1
cuando quieras respuesta casi instantánea.

## Manejo de rate limits y caché

- `api_cache` (tabla Supabase) guarda la respuesta cruda de INEGI por
  `cache_key = hash(indicador_ids + area + periodo)` con `expires_at`. INEGI
  publica ENOE/EMIM con periodicidad mensual/trimestral — no tiene sentido
  pedir el mismo indicador dos veces en el mismo mes. TTL sugerido: 25 días.
- Los colectores de vacantes usan la misma tabla `api_cache` para no volver a
  descargar una página de listado ya vista en las últimas N horas, y respetan
  un `REQUEST_DELAY_SECONDS` configurable (por defecto 3-5s) entre requests
  al mismo host.
- `collection_runs` registra cada corrida (fuente, sector, inicio/fin,
  registros obtenidos, error) — sirve como bitácora y para detectar fuentes
  caídas antes de reintentar agresivamente.
