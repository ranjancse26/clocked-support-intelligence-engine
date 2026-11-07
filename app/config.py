from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mock_mode: bool = True
    database_url: str = "sqlite:///./support.db"
    clocked_api_key: str | None = None
    typellm_api_key: str | None = None
    clocked_base_url: str = "https://clocked.rezolve.ai/clocked"
    refund_requires_approval: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
