# Análisis de seguridad con Nuclei — Backend (jwt-fastapi-items)

Análisis de vulnerabilidades del **backend Marvel** (API FastAPI de items) usando
**Nuclei** de ProjectDiscovery dentro de un contenedor Docker.

- **Fecha del análisis:** 2026-10-14
- **Objetivo escaneado:** `http://jwt-items:8001` (contenedor `jwt-items`)
- **Imagen:** `projectdiscovery/nuclei:latest` (nuclei v3.11.1)
- **Plantillas:** `nuclei-templates v10.5.0` (11.154 plantillas)
- **Resultado crudo:** [`nuclei-items.jsonl`](nuclei-items.jsonl)

## Cómo se ejecutó

Nuclei se conectó a la **red del stack** (`practicajwt_app-net`) para alcanzar el
servicio por su nombre dentro de Docker (bridging entre contenedores):

```bash
docker run --rm --network practicajwt_app-net \
  -v nuclei-templates:/root/nuclei-templates \
  -v "$PWD/security/nuclei:/reports" \
  projectdiscovery/nuclei:latest \
  -target http://jwt-items:8001 \
  -severity info,low,medium,high,critical \
  -jsonl-export /reports/nuclei-items.jsonl -stats -no-color
```

## Hallazgos (14)

Todas las coincidencias son de severidad **info** (sin vulnerabilidades
críticas/altas explotables detectadas de caja negra).

| Severidad | Plantilla | Hallazgo |
|---|---|---|
| info | `swagger-api` | **Swagger UI público** (`/docs`) accesible |
| info | `redoc-api-docs` | **ReDoc** (`/redoc`) accesible |
| info | `openapi` | Especificación **OpenAPI** expuesta (`/openapi.json`) |
| info | `tech-detect` | Fingerprinting de tecnología |
| info | `http-missing-security-headers` (×10) | Faltan cabeceras de seguridad |

### Cabeceras de seguridad ausentes en el backend

`Content-Security-Policy`, `Permissions-Policy`, `X-Frame-Options`,
`X-Permitted-Cross-Domain-Policies`, `Cross-Origin-Resource-Policy`,
`X-Content-Type-Options`, `Referrer-Policy`, `Cross-Origin-Embedder-Policy`,
`Cross-Origin-Opener-Policy`, `Strict-Transport-Security`.

## Interpretación

1. **Documentación de API expuesta (Swagger/ReDoc/OpenAPI).** Superficie de
   información: revela todos los endpoints, esquemas y modelos. En producción
   debe deshabilitarse o protegerse; es el hallazgo más relevante de este repo.
2. **Cabeceras de seguridad ausentes.** Uvicorn/FastAPI no las añade por
   defecto; se corrigen con un middleware (o en el nginx que hace de proxy).
3. Sin vulnerabilidades explotables de Nuclei en los endpoints escaneados
   (el acceso a `/items` exige JWT válido: los 401 se comportan correctamente).

## Estado

Correcciones aplicadas, **cada una con su prueba**:

- [x] Deshabilitar/proteger `/docs`, `/redoc` y `/openapi.json` por defecto
      (`DOCS_ENABLED=1` para habilitarlos en desarrollo).
      Validado por [`tests/test_docs_disabled.py`](../../tests/test_docs_disabled.py)
      y [`security/evidence/fix-docs-disabled.md`](../evidence/fix-docs-disabled.md).
- [x] Middleware de cabeceras de seguridad (`security_headers.py`).
      Validado por [`tests/test_security_headers.py`](../../tests/test_security_headers.py)
      y [`security/evidence/fix-security-headers.md`](../evidence/fix-security-headers.md).

> Tras las correcciones hay que reconstruir la imagen del backend
> (`docker compose build items && docker compose up -d items`) y volver a
> lanzar Nuclei para confirmar que los hallazgos desaparecen.
