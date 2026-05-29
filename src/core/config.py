from pydantic_settings import BaseSettings

#BaseSettings is used to manage application configuration/settings.
#It automatically reads values from:

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres@localhost:5432/banyan_employees"
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300

    class Config:
        env_file = ".env"


settings = Settings()
