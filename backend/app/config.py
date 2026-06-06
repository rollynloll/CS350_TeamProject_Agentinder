from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    database_url: str
    openai_api_key: str = ""
    app_env: str = "development"
    auto_match_interval_seconds: int = 300  # 자율 스와이프 루프 주기 (기본 5분)


settings = Settings()
