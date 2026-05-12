from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    SUPABASE_URL: str = "https://kpkpxvjnaptduudgbfcq.supabase.co"
    SUPABASE_KEY: str = ""
    SUPABASE_DB_URL: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 150
    OPENAI_HARD_LIMIT_USD: float = 10.0

    # Security
    SECRET_KEY: str = "change-this-in-production-use-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # App
    ENVIRONMENT: str = "production"
    CORS_ORIGINS: str = "https://your-app.vercel.app"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Model paths (relative to backend/ working directory)
    MODEL_PATH: str = "./models/saved_model.pkl"
    SHAP_BACKGROUND_PATH: str = "./models/shap_background.pkl"
    FEATURE_COLUMNS_PATH: str = "./models/feature_columns.pkl"

    # Amazon / Scavio
    SCAVIO_API_KEY: str = ""
    AMAZON_ASSOCIATE_ID: str = "xairecommende-21"

    @field_validator("SUPABASE_DB_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if v and not v.startswith("postgresql+asyncpg://"):
            raise ValueError("SUPABASE_DB_URL must use postgresql+asyncpg:// scheme")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        # Always allow the production domain
        origins.extend([
            "https://xairecommender.me",
            "https://www.xairecommender.me",
        ])
        if self.ENVIRONMENT == "development":
            origins.extend([
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
            ])
        return list(dict.fromkeys(origins))  # deduplicate, preserve order

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
