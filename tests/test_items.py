"""Pruebas de la API de items.

* Unitarias: verificación de JWT (válido, alterado, expirado, `alg: none`).
* Integración: contra http://localhost:8001 con el stack levantado.

    pytest -q                      # sólo unitarias
    RUN_INTEGRATION=1 pytest -q     # unitarias + integración
"""

import datetime as dt
import os

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import JWT_AUDIENCE, JWT_ISSUER
from app.security import get_current_user

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"
ITEMS_URL = os.getenv("ITEMS_URL", "http://localhost:8001")
AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8000")

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
PUBLIC_PEM = KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def make_token(**overrides) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": "caleb",
        "dn": "uid=caleb,ou=users,dc=example,dc=com",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + dt.timedelta(minutes=30),
    }
    payload.update(overrides)
    return jwt.encode(payload, PRIVATE_PEM, algorithm="RS256")


class FakeCredentials:
    def __init__(self, token: str | None):
        self.credentials = token


def check(token: str | None):
    """Atajo para ejercitar la dependencia de seguridad directamente."""
    from fastapi import HTTPException

    try:
        return get_current_user(FakeCredentials(token))
    except HTTPException as exc:
        return exc


# --------------------------------------------------------------------------
# Unitarias
# --------------------------------------------------------------------------
def test_token_valido_devuelve_el_usuario(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    user = check(make_token())
    assert user.username == "caleb"
    assert user.dn == "uid=caleb,ou=users,dc=example,dc=com"


def test_sin_token_es_401(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    exc = check(None)
    assert exc.status_code == 401
    assert exc.detail == "Missing bearer token"


def test_token_alterado_es_401(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    token = make_token()
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-4]}AAAA"
    assert check(tampered).status_code == 401


def test_token_firmado_con_otra_clave_es_401(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert check(jwt.encode({"sub": "admin"}, other, algorithm="RS256")).status_code == 401


def test_alg_none_es_401(monkeypatch):
    """El servicio fija algorithms=['RS256']; 'none' nunca se acepta."""
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    forged = jwt.encode(
        {"sub": "admin", "iss": JWT_ISSUER, "aud": JWT_AUDIENCE}, key="", algorithm="none"
    )
    assert check(forged).status_code == 401


def test_token_expirado_es_401(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    expired = make_token(
        iat=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2),
        nbf=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2),
        exp=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
    )
    exc = check(expired)
    assert exc.status_code == 401
    assert "expired" in exc.detail.lower()


def test_otra_audiencia_es_401(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    assert check(make_token(aud="otra-api")).status_code == 401


def test_otro_issuer_es_401(monkeypatch):
    monkeypatch.setattr("app.security.public_key", lambda: PUBLIC_PEM)
    assert check(make_token(iss="issuer-falso")).status_code == 401


# --------------------------------------------------------------------------
# Integración
# --------------------------------------------------------------------------
requires_stack = pytest.mark.skipif(
    not RUN_INTEGRATION, reason="requiere RUN_INTEGRATION=1 y el stack levantado"
)


def login(username: str, password: str) -> str:
    import httpx

    response = httpx.post(
        f"{AUTH_URL}/auth/login", json={"username": username, "password": password}, timeout=15
    )
    response.raise_for_status()
    return response.json()["access_token"]


@requires_stack
def test_items_sin_token_devuelve_401():
    import httpx

    response = httpx.get(f"{ITEMS_URL}/items", timeout=15)
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


@requires_stack
def test_ciclo_completo_de_un_item():
    import httpx

    token = login("ivan", "ivan123")
    headers = {"Authorization": f"Bearer {token}"}

    created = httpx.post(
        f"{ITEMS_URL}/items",
        headers=headers,
        json={"name": "Loki", "category": "Series", "image_url": "/posters/wanda.svg", "note": "prueba"},
        timeout=15,
    )
    assert created.status_code == 201
    item = created.json()
    assert item["username"] == "ivan"  # la identidad viene del claim sub
    assert item["favorite"] is False

    listed = httpx.get(f"{ITEMS_URL}/items", headers=headers, timeout=15).json()
    assert any(i["id"] == item["id"] for i in listed["items"])
    assert listed["username"] == "ivan"

    patched = httpx.patch(
        f"{ITEMS_URL}/items/{item['id']}", headers=headers, json={"favorite": True}, timeout=15
    )
    assert patched.json()["favorite"] is True

    deleted = httpx.delete(f"{ITEMS_URL}/items/{item['id']}", headers=headers, timeout=15)
    assert deleted.status_code == 204

    again = httpx.delete(f"{ITEMS_URL}/items/{item['id']}", headers=headers, timeout=15)
    assert again.status_code == 404


@requires_stack
def test_un_usuario_no_ve_ni_toca_items_de_otro():
    import httpx

    caleb = {"Authorization": f"Bearer {login('caleb', 'caleb123')}"}
    ivan = {"Authorization": f"Bearer {login('ivan', 'ivan123')}"}

    created = httpx.post(
        f"{ITEMS_URL}/items", headers=caleb, json={"name": "Item secreto de caleb", "category": "Otros"},
        timeout=15,
    ).json()

    # ivan no lo ve en su lista
    ids = [i["id"] for i in httpx.get(f"{ITEMS_URL}/items", headers=ivan, timeout=15).json()["items"]]
    assert created["id"] not in ids

    # ni puede editarlo ni borrarlo
    assert httpx.patch(
        f"{ITEMS_URL}/items/{created['id']}", headers=ivan, json={"favorite": True}, timeout=15
    ).status_code == 404
    assert httpx.delete(f"{ITEMS_URL}/items/{created['id']}", headers=ivan, timeout=15).status_code == 404

    httpx.delete(f"{ITEMS_URL}/items/{created['id']}", headers=caleb, timeout=15)


@requires_stack
def test_el_body_no_puede_cambiar_el_usuario():
    """El campo username del body se ignora: manda el claim sub."""
    import httpx

    token = login("ivan", "ivan123")
    created = httpx.post(
        f"{ITEMS_URL}/items",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Intento de suplantación", "category": "Otros", "username": "caleb"},
        timeout=15,
    ).json()
    assert created["username"] == "ivan"
    httpx.delete(
        f"{ITEMS_URL}/items/{created['id']}", headers={"Authorization": f"Bearer {token}"}, timeout=15
    )
