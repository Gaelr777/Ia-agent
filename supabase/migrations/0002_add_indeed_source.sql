-- Agrega Indeed como fuente de vacantes de tipo 'manual': los datos no se
-- recolectan por un cron automatizado (el conector de Indeed disponible en
-- sesiones de chat de Claude no es una credencial reutilizable en GitHub
-- Actions), sino vía el flujo asistido de
-- pipeline/collectors/vacantes/indeed_manual.py + el workflow
-- indeed-manual-import.yml. Ver docs/LEGAL_TOS.md.
insert into job_sources (name, base_url, collection_method, tos_risk_level, enabled) values
  ('indeed', 'https://www.indeed.com', 'manual', 'low', true)
on conflict (name) do nothing;
