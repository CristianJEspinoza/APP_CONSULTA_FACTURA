from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuracion de la aplicacion cargada desde variables de entorno."""

    # API Lucode
    API_URL_BASE: str = "https://dev.apisunat.pe/api/v1/sunat/comprobante"
    API_TOKEN_LUCODE: str = ""

    # API Tracker SUNAT — datos del proveedor (condicion, estado, estado del comprobante)
    API_URL_SUNAT_TRACKER: str = (
        "https://ms-tracker-sunat-f3h4f6eec3exd5dc.westus-01.azurewebsites.net"
        "/api/sunat/consulta"
    )
    API_KEY_SUNAT_TRACKER: str = ""

    # Seguridad — API Key para proteger esta API
    API_KEY: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Ignora variables de entorno extra (p. ej. PeruDevs heredadas) en vez
        # de fallar el arranque con extra_forbidden.
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado de la configuracion."""
    return Settings()
