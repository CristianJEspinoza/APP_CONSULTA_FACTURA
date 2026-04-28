from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.config import get_settings

API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> str:
    """
    Dependencia de seguridad que valida el API Key del header Authorization.
    Lanza 401 si no se proporciona o es inválido.
    """
    settings = get_settings()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Envía el header 'Authorization'.",
        )

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida.",
        )

    return api_key
