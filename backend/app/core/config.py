import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "haoxhealth-ai"
    debug: bool = False
    database_url: str = "sqlite:///./haoxhealth.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    access_token_expire_minutes: int = 60

    amap_api_key: str = ""
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_timeout_seconds: float = 30.0
    dashscope_max_retries: int = 1
    tool_timeout_seconds: float = 15.0
    kb_search_endpoint: str = ""
    kb_search_api_key: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
