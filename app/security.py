"""Bearer token validation (RS256 signature check)."""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_PUBLIC_KEY_FILE,
    read_secret_file,
)

bearer_scheme = HTTPBearer(auto_error=False, description="JWT issued by jwt-ldap-auth")


@lru_cache(maxsize=1)
def public_key() -> str:
    return read_secret_file(JWT_PUBLIC_KEY_FILE)


@dataclass(frozen=True)
class CurrentUser:
    username: str
    dn: str

    @property
    def label(self) -> str:
        return f"{self.dn}"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Every protected route goes through here: no valid token, no data."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            public_key(),
            algorithms=["RS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired, log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(username=payload["sub"], dn=payload.get("dn", ""))
