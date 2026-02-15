from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "Intelligent Academic Planner"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # SECURITY
    SECRET_KEY: str = "change_this_secret_key_to_something_secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # DATABASE (async PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/iap_db"

    # GOOGLE OAUTH  (from System B)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # WEBHOOKS  (from System B)
    WEBHOOK_BASE_URL: str = ""

    # SERVER
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

settings = Settings()
