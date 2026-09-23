from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"

    # Tells Pydantic to read from a .env file automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instantiated once as a global settings object
settings = Settings()
