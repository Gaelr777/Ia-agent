# Monitor de Mercado Laboral MX

Pipeline ligero (sin frameworks de agentes) que:

1. Clasifica el sector laboral (SCIAN) de un usuario a partir de su CV,
   usando la API de Claude.
2. Recolecta datos periódicos de INEGI, del Portal del Empleo (y
   opcionalmente OCC Mundial/Computrabajo) para ese sector.
3. Extrae habilidades técnicas y blandas demandadas en las vacantes.
4. Genera un reporte mensual comparativo, almacenado en Supabase para que
   el frontend lo consuma.

## Dónde empezar a leer

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — diagrama de módulos y por
  qué esta arquitectura (y no CrewAI/LangGraph/AutoGen).
- [`docs/SETUP.md`](docs/SETUP.md) — cómo obtener Supabase, token INEGI y
  API key de Anthropic desde cero, y correr el pipeline en local.
- [`docs/LEGAL_TOS.md`](docs/LEGAL_TOS.md) — qué fuentes de vacantes usar y
  cuáles evitar, y por qué.
- [`supabase/migrations/0001_init.sql`](supabase/migrations/0001_init.sql) —
  esquema completo de base de datos.

## Estructura

```
pipeline/
  cv_classifier/     # Paso 1: CV -> sector SCIAN (independiente del resto)
  collectors/
    inegi/           # Paso 2a: series de INEGI (ENOE, EMIM, IGAE...)
    vacantes/        # Paso 2b: vacantes por sector
  analysis/          # Paso 3: skills + tendencias + reporte mensual
  common/            # cliente Supabase, caché, config compartida
.github/workflows/
  process-cv.yml         # se dispara cuando alguien sube un CV
  monthly-collection.yml # cron mensual + dispatch manual por sector
supabase/migrations/     # esquema SQL
data/scian_sectors.json  # catálogo SCIAN 2018 (sectores de 2 dígitos)
```

## Sector piloto

El pipeline se probó primero con **Manufactura / Industria (SCIAN 31-33)**,
que además tiene la ventaja de estar cubierto en detalle por la Encuesta
Mensual de la Industria Manufacturera (EMIM) de INEGI. El paso de
recolección/análisis (`collectors/`, `analysis/`) es agnóstico al sector —
reutilízalo para cualquier otro código SCIAN cambiando el parámetro
`--sector`.
