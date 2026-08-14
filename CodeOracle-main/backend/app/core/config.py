import os
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    APP_NAME: str = "CodeOracle"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    ENV: str = os.getenv("ENVIRONMENT") or os.getenv("ENV", "development")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT") or os.getenv("ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    TEMP_DIR: str = os.getenv("CODEORACLE_TEMP_DIR", "")
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,*").split(",")
        if origin.strip()
    ]


settings = Settings()
