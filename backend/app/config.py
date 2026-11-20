import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> str:
    """
    Locates the .env file whether running from /backend, repository root, or Docker.
    """
    # 1. Look in backend directory relative to config.py
    backend_env = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    if os.path.exists(backend_env):
        return backend_env

    # 2. Look in current working directory
    cwd_env = os.path.join(os.getcwd(), ".env")
    if os.path.exists(cwd_env):
        return cwd_env

    # 3. Look in cwd/backend/.env
    nested_env = os.path.join(os.getcwd(), "backend", ".env")
    if os.path.exists(nested_env):
        return nested_env

    return ".env"


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./var/ambatufit.db"
    JWT_SECRET: str = "ambatufit-development-jwt-super-secret-key-32chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_MINUTES: int = 120
    CORS_ORIGINS: str = "http://localhost:19006,http://localhost:8081,http://127.0.0.1:19006,http://localhost:8080"
    
    # Off-STB AI service
    AI_INFERENCE_URL: str = "http://127.0.0.1:8100/internal/v1/infer"
    AI_INFERENCE_TOKEN: str = "replace-for-external-host-ai-token"
    AI_TIMEOUT_SECONDS: float = 4.0
    
    # Off-STB Integration service
    INTEGRATION_API_BASE_URL: str = "http://127.0.0.1:8200/integration/v1"
    INTEGRATION_API_TOKEN: str = "replace-for-external-host-integration-token"
    INTEGRATION_TIMEOUT_SECONDS: float = 5.0
    INTEGRATION_MODE: str = "mock"  # mock or live
    
    # Partner API Keys for server-to-server calls to AmbatuFit
    # Format: "provider_id:api_key,provider_id2:api_key2"
    PARTNER_API_KEYS: str = "ambatunoutrish:noutrish-sec-key-123,ambatomove:move-sec-key-456"

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def partner_key_dict(self) -> dict[str, str]:
        keys = {}
        for entry in self.PARTNER_API_KEYS.split(","):
            if ":" in entry:
                provider, key = entry.split(":", 1)
                keys[key.strip()] = provider.strip()
        return keys


settings = Settings()
