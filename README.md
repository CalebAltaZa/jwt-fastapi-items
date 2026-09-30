# jwt-fastapi-items

API de la lista de items Marvel. **Todas las rutas de datos exigen un JWT
válido**: la firma se verifica con la clave **publica** RS256 y el usuario de
cada item se toma del claim `sub` del token, nunca de lo que mande el cliente.

## Stack

- FastAPI + Uvicorn
- `PyJWT` + `cryptography` para verificar RS256
- SQLite (biblioteca estandar, sin dependencias extra)

## Endpoints

| Metodo | Ruta | Token | Descripcion |
| --- | --- | --- | --- |
| `GET` | `/health` | no | Estado del servicio |
| `GET` | `/categories` | no | Categorias disponibles |
| `GET` | `/items` | si | Items del usuario autenticado |
| `POST` | `/items` | si | Crea un item para el usuario autenticado |
| `PATCH` | `/items/{id}` | si | Edita campos y/o marca favorito |
| `DELETE` | `/items/{id}` | si | Elimina un item propio |

### Ejemplos

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"caleb","password":"caleb123"}' \
  | sed 's/.*"access_token":"\([^"]*\)".*/\1/')

curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/items

curl -X POST http://localhost:8001/items \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Avengers: Doomsday","category":"Películas",
       "image_url":"https://…/poster.jpg","note":"La nueva saga"}'

curl -X PATCH http://localhost:8001/items/1 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"favorite":true}'

curl -X DELETE http://localhost:8001/items/1 -H "Authorization: Bearer $TOKEN"
```

Sin token: `401 {"detail":"Missing bearer token"}`.
Con token de otro emisor, otra audiencia, expirado o alterado: `401`.
Con un `id` de otro usuario: `404` (no se revela que ese item existe).

## Modelo de datos (SQLite)

```sql
CREATE TABLE items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL,   -- claim sub del JWT
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,
    image_url  TEXT,
    note       TEXT,
    favorite   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_items_username ON items(username);
```

## Aislamiento entre usuarios

Todas las consultas filtran por el `sub` del token:

```python
rows = connection.execute(
    "SELECT * FROM items WHERE username = ? ORDER BY favorite DESC, created_at DESC",
    (user.username,),          # user viene del token, no del body
).fetchall()
```

Lo mismo aplica a `PATCH` y `DELETE` (`WHERE id = ? AND username = ?`), por lo que
un usuario nunca puede leer, editar ni borrar items de otro.

## Verificacion del token

```python
jwt.decode(
    token,
    public_key(),            # /secrets/jwt_public.pem
    algorithms=["RS256"],    # explícito: bloquea "alg: none"
    audience="jwt-items",
    issuer="jwt-ldap-auth",
)
```

Este servicio **solo** recibe la clave publica: no puede emitir tokens aunque se
comprometa, porque la privada vive en el volumen del servicio de auth.

## Variables de entorno

| Variable | Default | Descripcion |
| --- | --- | --- |
| `JWT_PUBLIC_KEY_FILE` | `/secrets/jwt_public.pem` | Clave publica (montada `:ro`) |
| `JWT_ISSUER` | `jwt-ldap-auth` | Issuer esperado |
| `JWT_AUDIENCE` | `jwt-items` | Audiencia esperada |
| `DB_PATH` | `/data/items.db` | Ruta del archivo SQLite |

## Datos de demostracion

```bash
docker compose exec items python -m app.seed --user caleb
```

Carga 12 items Marvel (los dos primeros como favoritos). Es idempotente: si el
usuario ya tiene items, no inserta nada.

## Correr con Docker

```bash
docker build -t jwt-fastapi-items .
docker run --rm -p 8001:8001 \
  -v jwt_items_secrets:/secrets:ro \
  -v items_data:/data \
  jwt-fastapi-items
```

Documentacion interactiva: http://localhost:8001/docs
