"""Dependências FastAPI (ex.: validação de API key)."""
from fastapi import Header, HTTPException

from src.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")
    return x_api_key
