import os
from pathlib import Path


def read_secret_file(path: str) -> str:
    """Read a secret from the mounted volume (here: only the public key)."""
    return Path(path).read_text().strip()


# --- JWT (only the PUBLIC key is mounted here: this service validates,
#     it can never sign a token) ------------------------------------------------
JWT_PUBLIC_KEY_FILE = os.getenv("JWT_PUBLIC_KEY_FILE", "/secrets/jwt_public.pem")
JWT_ISSUER = os.getenv("JWT_ISSUER", "jwt-ldap-auth")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "jwt-items")

# --- Database ----------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "/data/items.db")

# --- Catalog -----------------------------------------------------------------
CATEGORIES = [
    "Películas",
    "Series",
    "Cómics",
    "Personajes",
    "Videojuegos",
    "Mercancía",
    "Otros",
]
