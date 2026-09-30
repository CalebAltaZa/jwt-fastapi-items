"""Items API: every operation requires a valid Bearer JWT (RS256)."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .config import CATEGORIES, JWT_ISSUER
from .db import get_conn, init_db, now_iso, row_to_item
from .models import Item, ItemCreate, ItemUpdate
from .security import CurrentUser, get_current_user, public_key


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Marvel Items API",
    description=(
        "API de la lista de 'cosas que me gustan'. Protegida con JWT (RS256): "
        "recibe el Bearer token emitido por jwt-ldap-auth y valida firma, "
        "emisor, audiencia y expiración en cada request."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "items",
        "expects_issuer": JWT_ISSUER,
        "public_key_loaded": bool(public_key()),
    }


@app.get("/categories")
def categories():
    return {"categories": CATEGORIES}


@app.get("/items", response_model=dict)
def list_items(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
):
    """Lista únicamente los items del usuario autenticado (claim `sub`)."""
    with get_conn() as connection:
        rows = connection.execute(
            "SELECT * FROM items WHERE username = ? "
            "ORDER BY favorite DESC, created_at DESC, id DESC",
            (user.username,),
        ).fetchall()
    response.headers["X-Auth-Subject"] = user.username
    return {"username": user.username, "count": len(rows), "items": [row_to_item(r) for r in rows]}


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    user: CurrentUser = Depends(get_current_user),
):
    data = payload.normalized()
    with get_conn() as connection:
        cursor = connection.execute(
            "INSERT INTO items (username, name, category, image_url, note, favorite, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (
                user.username,
                data["name"],
                data["category"],
                data["image_url"],
                data["note"],
                now_iso(),
            ),
        )
        row = connection.execute(
            "SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return row_to_item(row)


@app.patch("/items/{item_id}", response_model=Item)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Edita campos y/o marca/desmarca favorito (solo de items propios)."""
    fields = payload.model_dump(exclude_unset=True)
    if "category" in fields and fields["category"] not in CATEGORIES:
        fields["category"] = "Otros"
    if "name" in fields:
        fields["name"] = fields["name"].strip()
    for optional in ("image_url", "note"):
        if optional in fields:
            fields[optional] = (fields[optional] or "").strip() or None
    if "favorite" in fields:
        fields["favorite"] = int(bool(fields["favorite"]))

    if fields:
        assignments = ", ".join(f"{column} = ?" for column in fields)
        with get_conn() as connection:
            cursor = connection.execute(
                f"UPDATE items SET {assignments} WHERE id = ? AND username = ?",
                (*fields.values(), item_id, user.username),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Item not found")
            row = connection.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)
            ).fetchone()
    else:
        with get_conn() as connection:
            row = connection.execute(
                "SELECT * FROM items WHERE id = ? AND username = ?", (item_id, user.username)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Item not found")

    return row_to_item(row)


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, user: CurrentUser = Depends(get_current_user)):
    with get_conn() as connection:
        cursor = connection.execute(
            "DELETE FROM items WHERE id = ? AND username = ?", (item_id, user.username)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
