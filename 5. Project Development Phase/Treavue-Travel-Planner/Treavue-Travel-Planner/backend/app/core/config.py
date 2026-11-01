import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "Treavue API")
        self.app_env = os.getenv("APP_ENV", "development")
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.port = int(os.getenv("PORT", "8000"))
        if not 1 <= self.port <= 65535:
            raise ValueError(f"PORT must be between 1 and 65535, got {self.port!r}")
        self.allowed_origins = _parse_origins(os.getenv("ALLOWED_ORIGINS"))
        if not self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin.")
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_auth_api_key = os.getenv("SUPABASE_AUTH_API_KEY", "").strip()
    def get_gemini_api_key(self) -> str:
        load_dotenv(dotenv_path=ENV_FILE, override=False)
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            return api_key
        return (dotenv_values(dotenv_path=ENV_FILE).get("GEMINI_API_KEY") or "").strip()


settings = Settings()
