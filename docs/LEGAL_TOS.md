# Fuentes de vacantes: legalidad, ToS y recomendación

Resumen ejecutivo: **usa el Portal del Empleo (gob.mx) como fuente primaria de
vacantes; trata a OCC Mundial/Computrabajo como fuente secundaria opcional de
bajo volumen y alto cuidado legal; evita LinkedIn e Indeed para recolección
automatizada.**

## 1. Portal del Empleo / Servicio Nacional de Empleo (empleo.gob.mx) — recomendado

- Es un portal público operado por la STPS (Secretaría del Trabajo y
  Previsión Social), pensado explícitamente para sindicar vacantes a
  terceros (agencias estatales de empleo, universidades, etc.).
- Al ser información gubernamental de interés público sobre vacantes
  agregadas de empleadores (no datos personales de individuos), el riesgo
  bajo LFPDPPP es mucho menor que scrapear perfiles/CVs de personas.
- **Antes de programar el scraper**: verifica si expone un *web service* /
  feed oficial para sindicación (muchos portales de bolsa de trabajo
  gubernamentales sí lo tienen, para que otros portales estatales lo
  consuman). Si existe, úsalo — es la opción más estable y sin riesgo ToS.
  Si no encuentras documentación pública, contempla escribir a la STPS/CGSNE
  pidiendo acceso — es una dependencia de gobierno con mandato de
  transparencia y datos abiertos (ver también `datos.gob.mx`, catálogo con
  tag `empleo`/`trabajo`).
- Si terminas haciendo scraping ligero de las páginas públicas de resultados
  de búsqueda (sin login, sin CVs de candidatos, solo el listado de
  vacantes), respeta `robots.txt`, identifica tu bot con un User-Agent
  claro y un contacto, y limita la frecuencia (ver `common/cache.py`).
- **Estado real (2026-07-07):** encontramos y confirmamos la API JSON
  interna del portal (`POST /api/Login/busqueda/empleos`, ver
  `pipeline/collectors/vacantes/empleo_gob.py`), pero devuelve HTTP 403 al
  llamarla desde GitHub Actions — no es un bloqueo general de IP (la
  página principal del sitio sí responde 200 desde el mismo runner), así
  que probablemente el endpoint de búsqueda requiere algún tipo de sesión
  o token que no hemos identificado. Pendiente de investigar más, o de
  preguntarle directamente a la STPS/CGSNE por un canal de sindicación
  oficial para terceros (sería la solución más robusta y sin esta
  fragilidad técnica).
## 2. OCC Mundial y Computrabajo — opcional, con precaución

- Son plataformas comerciales privadas. Sus avisos legales/ToS
  típicamente prohíben la extracción automatizada, el uso de bots/crawlers
  y la reutilización comercial de su contenido sin autorización (esto es
  estándar en portales de empleo, que ven las vacantes agregadas como un
  activo competitivo).
- Ninguna de las dos ofrece hoy una API pública self-service de vacantes.
- Riesgo legal en México: si haces scraping con fines que puedan
  interpretarse como comerciales y violas el ToS expreso, existe base para
  un reclamo civil por incumplimiento contractual (los ToS de un sitio
  público suelen considerarse un "contrato de adhesión" que aceptas al
  usarlo), y en teoría PROFECO podría interesarse bajo teorías de
  competencia desleal si el uso es comercial. El riesgo sobre datos
  *personales* (LFPDPPP) es menor aquí porque una vacante no es un dato
  personal de un individuo — pero el nombre/contacto del reclutador sí
  podría serlo, así que evita capturar y almacenar esos campos.
- **Recomendación práctica**: si decides incluirlas, hazlo como colector
  *opcional* (flag `ENABLE_OCC=false` / `ENABLE_COMPUTRABAJO=false` por
  defecto), a volumen bajo (unas cuantas búsquedas por sector al mes, no
  miles de páginas), sin evadir ningún control anti-bot, respetando
  `robots.txt`, y sin quedarte con datos de contacto de reclutadores. Para
  un uso en producción/comercial a mayor escala, la vía correcta es
  contactar a la empresa y negociar acceso a datos o un partnership — igual
  que pediría cualquier cliente de datos agregados de empleo (Revelo,
  Lightcast, etc. lo hacen así).
- El código incluido (`pipeline/collectors/vacantes/occ_mundial.py`) está
  deshabilitado por defecto y documentado como "usar bajo tu propio
  criterio legal", no como recomendación de uso en producción sin revisión.

## 3. LinkedIn Jobs — no recomendado para automatización

- LinkedIn tiene un historial extenso de litigios contra scrapers (el caso
  hiQ Labs v. LinkedIn es el más citado) y ToS muy explícitos prohibiendo
  scraping, además de defensas técnicas activas (detección de bots, rate
  limiting agresivo, bloqueo de IP).
- Su API oficial de "Talent/Jobs" requiere ser socio aprobado
  (LinkedIn Talent Solutions), con proceso de aplicación y costo — no es
  self-service.
- **Recomendación**: no lo automatices. Si en algún momento quieres una
  muestra puntual de LinkedIn, hazlo manualmente o vía una sesión
  interactiva (no como parte del cron), y no lo persistas en el pipeline
  mensual automatizado.

## 4. Indeed — no recomendado para automatización

- Indeed cerró su API pública de búsqueda de empleos hace años; su
  `robots.txt` público bloquea explícitamente el crawling de rutas de
  listados de empleo (`/jobs/...`) para bots genéricos.
- El conector de Indeed disponible en *esta sesión de Claude* es una
  integración especial vinculada a tu cuenta de Claude/Anthropic — no es
  una API key que puedas usar desde un script en GitHub Actions. No sirve
  para el cron automatizado de este proyecto, solo para consultas puntuales
  dentro de un chat interactivo.
- **Recomendación**: no lo incluyas en el pipeline automatizado. Si más
  adelante Anthropic o Indeed ofrecen una integración programática estable
  y con licencia clara para este uso, se puede revisar.

## 5. Buenas prácticas generales de scraping para este proyecto

1. Siempre revisa y respeta `robots.txt` del dominio antes de scrapear.
2. Identifica tu bot con un `User-Agent` descriptivo y un email/URL de
   contacto (facilita que el sitio te contacte antes de bloquearte/demandar,
   en vez de ir directo a medidas legales).
3. Limita la frecuencia (`REQUEST_DELAY_SECONDS`, backoff exponencial en
   429/503) — nunca hagas scraping en paralelo agresivo.
4. No captures ni almacenes datos personales de individuos (nombres de
   candidatos, contactos de reclutadores, fotos). El interés de este
   proyecto es el agregado (título de vacante, sector, habilidades
   requeridas, salario si se publica), no perfiles de personas.
5. Cachea agresivamente (ver `common/cache.py`) para minimizar el número de
   requests reales por corrida mensual.
6. Documenta en `collection_runs` cada corrida — si una fuente empieza a
   fallar sistemáticamente (posible bloqueo), el pipeline debe degradarse
   con gracia (usar la última snapshot válida) y no reintentar
   agresivamente.
