from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuracion de la aplicacion cargada desde variables de entorno."""

    # API Lucode
    API_URL_BASE: str = "https://dev.apisunat.pe/api/v1/sunat/comprobante"
    API_TOKEN_LUCODE: str = ""

    # API PeruDevs
    API_URL_PERU_DEVS: str = "https://api.perudevs.com/api/v1/ruc"
    API_KEY_PERU_DEVS: str = ""

    # Seguridad — API Key para proteger esta API
    API_KEY: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado de la configuracion."""
    return Settings()
