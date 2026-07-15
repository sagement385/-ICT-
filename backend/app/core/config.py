"""Typed environment configuration with optional external service settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings; secrets are intentionally empty by default."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    public_data_api_key: str | None = Field(default=None, alias="PUBLIC_DATA_API_KEY")
    hira_api_key: str | None = Field(default=None, alias="HIRA_API_KEY")
    molit_traffic_api_key: str | None = Field(default=None, alias="MOLIT_TRAFFIC_API_KEY")
    naver_map_client_id: str | None = Field(default=None, alias="NAVER_MAP_CLIENT_ID")
    naver_map_client_secret: str | None = Field(default=None, alias="NAVER_MAP_CLIENT_SECRET")
    aihub_data_root: str | None = Field(default=None, alias="AIHUB_DATA_ROOT")
    aihub_api_key: str | None = Field(default=None, alias="AIHUB_API_KEY")
    its_node_link_data_root: str | None = Field(default=None, alias="ITS_NODE_LINK_DATA_ROOT")
    backend_api_base_url: str | None = Field(default=None, alias="BACKEND_API_BASE_URL")
    route_data_max_age_seconds: int | None = Field(default=None, alias="ROUTE_DATA_MAX_AGE_SECONDS")
    hospital_status_max_age_seconds: int | None = Field(default=None, alias="HOSPITAL_STATUS_MAX_AGE_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings snapshot."""

    return Settings()
