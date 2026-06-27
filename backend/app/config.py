from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/einvoicing"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    MOCK_PROVIDER_URL: str = "http://localhost:8001"
    EINVOICE_BE_API_KEY: str = ""
    EINVOICE_BE_ENV: str = "staging"  # "staging" or "production"

    class Config:
        env_file = ".env"


settings = Settings()
