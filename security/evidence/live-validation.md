# Validación en vivo — items (jwt-fastapi-items)

Fecha: 2026-10-29. Stack reconstruido con `./setup.sh`
(`docker compose up --build -d`) a partir de los commits de corrección.

## Documentación deshabilitada (`swagger-api`, `redoc-api-docs`, `openapi`)

```console
$ for p in /docs /redoc /openapi.json; do
    printf '%-16s -> ' "$p"; curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:8001$p"
  done
/docs            -> 404
/redoc           -> 404
/openapi.json    -> 404
```

## Tests de integración

```console
$ RUN_INTEGRATION=1 pytest -o addopts="" -p no:warnings
...
============================== 18 passed in 2.65s ==============================
```

Incluye el middleware de cabeceras (`http-missing-security-headers`) y las tres
rutas de documentación deshabilitadas.
