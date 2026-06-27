from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/einvoicing"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    MOCK_PROVIDER_URL: str = "http://localhost:8001"
    EINVOICE_BE_API_KEY: str = ""
    EINVOICE_BE_ENV: str = "staging"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    @property
    def async_database_url(self) -> str:
        # Railway provides postgresql:// — asyncpg requires postgresql+asyncpg://
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
