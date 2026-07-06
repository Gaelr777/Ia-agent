-- Monitor de Mercado Laboral MX — esquema inicial
-- Corre esto en el SQL Editor de Supabase o vía `supabase db push`.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Catálogo SCIAN (sectores de 2 dígitos, SCIAN 2018). Ver data/scian_sectors.json.
-- ---------------------------------------------------------------------------
create table if not exists sectors (
  scian_code   text primary key,        -- ej. '31-33', '54'
  scian_name   text not null,
  is_tracked   boolean not null default false,  -- true = se recolecta en el cron mensual
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Perfiles de usuario (complementa auth.users de Supabase Auth)
-- ---------------------------------------------------------------------------
create table if not exists profiles (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- CVs subidos
-- ---------------------------------------------------------------------------
create table if not exists cvs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users(id) on delete set null,
  file_name     text not null,
  storage_path  text not null,           -- ruta dentro del bucket 'cvs'
  mime_type     text not null,           -- application/pdf | application/vnd.openxmlformats...
  status        text not null default 'pending'
                check (status in ('pending', 'processing', 'classified', 'error')),
  error_message text,
  uploaded_at   timestamptz not null default now(),
  processed_at  timestamptz
);

create index if not exists idx_cvs_status on cvs(status);

-- ---------------------------------------------------------------------------
-- Clasificación de sector a partir del CV (salida de classify_sector.py)
-- ---------------------------------------------------------------------------
create table if not exists cv_sector_classifications (
  id                 uuid primary key default gen_random_uuid(),
  cv_id              uuid not null references cvs(id) on delete cascade,
  scian_code         text not null references sectors(scian_code),
  confidence         numeric(4,3) not null check (confidence between 0 and 1),
  rationale          text,               -- explicación breve del modelo
  alternative_codes  jsonb,              -- otros sectores candidatos con su score
  model_used         text not null,
  raw_model_output   jsonb not null,
  classified_at      timestamptz not null default now(),
  unique (cv_id)
);

-- ---------------------------------------------------------------------------
-- Series de INEGI que seguimos, mapeadas a un sector SCIAN
-- ---------------------------------------------------------------------------
create table if not exists inegi_series (
  id            uuid primary key default gen_random_uuid(),
  scian_code    text references sectors(scian_code),  -- null = indicador nacional, no ligado a un sector
  indicator_id  text not null,           -- ID numérico del indicador en el Banco de Indicadores INEGI
  source        text not null,           -- 'ENOE' | 'EMIM' | 'IGAE' | 'ITAEE' | otro
  description   text not null,
  frequency     text not null default 'monthly' check (frequency in ('monthly','quarterly','annual')),
  verified      boolean not null default false,  -- true tras confirmar el indicator_id con verify_series.py
  created_at    timestamptz not null default now(),
  unique (indicator_id, source)
);

-- ---------------------------------------------------------------------------
-- Snapshots de valores de esas series a lo largo del tiempo
-- ---------------------------------------------------------------------------
create table if not exists inegi_snapshots (
  id           uuid primary key default gen_random_uuid(),
  series_id    uuid not null references inegi_series(id) on delete cascade,
  period       date not null,            -- primer día del periodo (mes o trimestre)
  value        numeric,
  unit         text,
  fetched_at   timestamptz not null default now(),
  unique (series_id, period)
);

create index if not exists idx_inegi_snapshots_period on inegi_snapshots(period);

-- ---------------------------------------------------------------------------
-- Fuentes de vacantes
-- ---------------------------------------------------------------------------
create table if not exists job_sources (
  id                 uuid primary key default gen_random_uuid(),
  name               text not null unique,   -- 'empleo_gob_mx' | 'occ_mundial' | 'computrabajo'
  base_url           text not null,
  collection_method  text not null check (collection_method in ('api','scrape','manual')),
  tos_risk_level     text not null default 'low' check (tos_risk_level in ('low','medium','high')),
  enabled            boolean not null default true
);

-- ---------------------------------------------------------------------------
-- Vacantes recolectadas
-- ---------------------------------------------------------------------------
create table if not exists job_postings (
  id               uuid primary key default gen_random_uuid(),
  source_id        uuid not null references job_sources(id),
  external_id      text not null,        -- ID de la vacante en la fuente original
  scian_code       text references sectors(scian_code),
  title            text not null,
  company          text,
  location         text,
  salary_min       numeric,
  salary_max       numeric,
  posted_at        date,
  description_url  text,
  description_raw  text,                 -- texto de la vacante, usado por skills_extraction.py
  snapshot_month   date not null,        -- primer día del mes de la corrida que la recolectó
  collected_at     timestamptz not null default now(),
  unique (source_id, external_id, snapshot_month)
);

create index if not exists idx_job_postings_sector_month on job_postings(scian_code, snapshot_month);

-- ---------------------------------------------------------------------------
-- Catálogo normalizado de habilidades (para deduplicar variantes: "Python",
-- "python3", "Programación en Python" -> mismo normalized_name)
-- ---------------------------------------------------------------------------
create table if not exists skills_catalog (
  id               uuid primary key default gen_random_uuid(),
  normalized_name  text not null unique,
  display_name     text not null,
  skill_type       text not null check (skill_type in ('hard','soft')),
  first_seen_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Habilidades detectadas por vacante (salida de skills_extraction.py)
-- ---------------------------------------------------------------------------
create table if not exists job_posting_skills (
  id               uuid primary key default gen_random_uuid(),
  job_posting_id   uuid not null references job_postings(id) on delete cascade,
  skill_id         uuid not null references skills_catalog(id),
  confidence       numeric(4,3) not null default 1.0 check (confidence between 0 and 1),
  unique (job_posting_id, skill_id)
);

create index if not exists idx_job_posting_skills_skill on job_posting_skills(skill_id);

-- ---------------------------------------------------------------------------
-- Reporte mensual agregado por sector (lo que consume el dashboard)
-- ---------------------------------------------------------------------------
create table if not exists monthly_sector_reports (
  id            uuid primary key default gen_random_uuid(),
  scian_code    text not null references sectors(scian_code),
  period        date not null,           -- primer día del mes del reporte
  report_json   jsonb not null,          -- estructura completa: métricas INEGI, top skills, deltas MoM
  summary_md    text,                    -- resumen en markdown listo para mostrar/enviar
  generated_at  timestamptz not null default now(),
  unique (scian_code, period)
);

-- ---------------------------------------------------------------------------
-- Caché genérico para no golpear repetidamente APIs externas
-- ---------------------------------------------------------------------------
create table if not exists api_cache (
  cache_key     text primary key,
  response_json jsonb not null,
  fetched_at    timestamptz not null default now(),
  expires_at    timestamptz not null
);

create index if not exists idx_api_cache_expires on api_cache(expires_at);

-- ---------------------------------------------------------------------------
-- Bitácora de corridas de recolección (observabilidad + detectar fuentes caídas)
-- ---------------------------------------------------------------------------
create table if not exists collection_runs (
  id                uuid primary key default gen_random_uuid(),
  source            text not null,       -- 'inegi' | 'empleo_gob_mx' | 'occ_mundial' | 'skills_extraction' | ...
  scian_code        text references sectors(scian_code),
  started_at        timestamptz not null default now(),
  finished_at       timestamptz,
  status            text not null default 'running' check (status in ('running','success','error')),
  records_collected integer default 0,
  error_message     text
);

create index if not exists idx_collection_runs_source_started on collection_runs(source, started_at desc);

-- ---------------------------------------------------------------------------
-- Seed: catálogo SCIAN (sectores de 2 dígitos)
-- ---------------------------------------------------------------------------
insert into sectors (scian_code, scian_name, is_tracked) values
  ('11', 'Agricultura, cría y explotación de animales, aprovechamiento forestal, pesca y caza', false),
  ('21', 'Minería', false),
  ('22', 'Generación, transmisión y distribución de energía eléctrica, suministro de agua y de gas natural por ductos al consumidor final', false),
  ('23', 'Construcción', false),
  ('31-33', 'Industrias manufactureras', true),
  ('43', 'Comercio al por mayor', false),
  ('46', 'Comercio al por menor', false),
  ('48-49', 'Transportes, correos y almacenamiento', false),
  ('51', 'Información en medios masivos', false),
  ('52', 'Servicios financieros y de seguros', false),
  ('53', 'Servicios inmobiliarios y de alquiler de bienes muebles e intangibles', false),
  ('54', 'Servicios profesionales, científicos y técnicos', false),
  ('55', 'Corporativos', false),
  ('56', 'Servicios de apoyo a los negocios y manejo de desechos y servicios de remediación', false),
  ('61', 'Servicios educativos', false),
  ('62', 'Servicios de salud y de asistencia social', false),
  ('71', 'Servicios de esparcimiento culturales y deportivos, y otros servicios recreativos', false),
  ('72', 'Servicios de alojamiento temporal y de preparación de alimentos y bebidas', false),
  ('81', 'Otros servicios excepto actividades gubernamentales', false),
  ('93', 'Actividades legislativas, gubernamentales, de impartición de justicia y de organismos internacionales y extraterritoriales', false)
on conflict (scian_code) do nothing;

-- ---------------------------------------------------------------------------
-- Seed: fuentes de vacantes
-- ---------------------------------------------------------------------------
insert into job_sources (name, base_url, collection_method, tos_risk_level, enabled) values
  ('empleo_gob_mx', 'https://www.empleo.gob.mx', 'scrape', 'low', true),
  ('occ_mundial',   'https://www.occ.com.mx',    'scrape', 'medium', false),
  ('computrabajo',  'https://www.computrabajo.com.mx', 'scrape', 'medium', false)
on conflict (name) do nothing;

-- ---------------------------------------------------------------------------
-- RLS: las tablas de datos del pipeline solo las escribe el service_role
-- (usado por GitHub Actions). El frontend lee con la anon key en modo
-- solo-lectura para las tablas de reporte/públicas.
-- ---------------------------------------------------------------------------
alter table sectors enable row level security;
alter table inegi_series enable row level security;
alter table inegi_snapshots enable row level security;
alter table job_sources enable row level security;
alter table job_postings enable row level security;
alter table skills_catalog enable row level security;
alter table job_posting_skills enable row level security;
alter table monthly_sector_reports enable row level security;
alter table cvs enable row level security;
alter table cv_sector_classifications enable row level security;
alter table profiles enable row level security;
alter table api_cache enable row level security;
alter table collection_runs enable row level security;

-- Lectura pública de los datos agregados/no sensibles (ajusta a tu gusto).
create policy "public read sectors" on sectors for select using (true);
create policy "public read inegi_series" on inegi_series for select using (true);
create policy "public read inegi_snapshots" on inegi_snapshots for select using (true);
create policy "public read job_postings" on job_postings for select using (true);
create policy "public read skills_catalog" on skills_catalog for select using (true);
create policy "public read job_posting_skills" on job_posting_skills for select using (true);
create policy "public read monthly_sector_reports" on monthly_sector_reports for select using (true);

-- Un usuario solo ve sus propios CVs y su propia clasificación.
create policy "user reads own cvs" on cvs for select using (auth.uid() = user_id);
create policy "user inserts own cvs" on cvs for insert with check (auth.uid() = user_id);
create policy "user reads own classification" on cv_sector_classifications for select
  using (exists (select 1 from cvs where cvs.id = cv_id and cvs.user_id = auth.uid()));
create policy "user reads/edits own profile" on profiles for all using (auth.uid() = user_id);

-- Nota: no se crean policies de INSERT/UPDATE para service_role porque ese
-- rol se salta RLS por diseño de Supabase (usa la service_role key, nunca
-- la anon key, en los scripts de pipeline/).
