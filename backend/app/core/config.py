"""Typed environment configuration with optional external service settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings; secrets are intentionally empty by default."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOWED_ORIGINS",
    )
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    public_data_api_key: str | None = Field(default=None, alias="PUBLIC_DATA_API_KEY")
    hira_api_key: str | None = Field(default=None, alias="HIRA_API_KEY")
    nemc_api_key: str | None = Field(default=None, alias="NEMC_API_KEY")
    molit_traffic_api_key: str | None = Field(default=None, alias="MOLIT_TRAFFIC_API_KEY")
    molit_traffic_base_url: str | None = Field(default=None, alias="MOLIT_TRAFFIC_BASE_URL")
    naver_map_client_id: str | None = Field(default=None, alias="NAVER_MAP_CLIENT_ID")
    naver_map_client_secret: str | None = Field(default=None, alias="NAVER_MAP_CLIENT_SECRET")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash-lite", alias="GEMINI_MODEL")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        alias="GEMINI_BASE_URL",
    )
    gemini_timeout_seconds: float = Field(
        default=20.0,
        ge=1.0,
        le=60.0,
        alias="GEMINI_TIMEOUT_SECONDS",
    )
    hira_base_url: str = Field(
        default="https://apis.data.go.kr/B551182/hospInfoServicev2",
        alias="HIRA_BASE_URL",
    )
    hira_detail_base_url: str = Field(
        default="https://apis.data.go.kr/B551182/MadmDtlInfoService2.8",
        alias="HIRA_DETAIL_BASE_URL",
    )
    nemc_base_url: str = Field(
        default="https://apis.data.go.kr/B552657/ErmctInfoInqireService",
        alias="NEMC_BASE_URL",
    )
    naver_directions_base_url: str = Field(
        default="https://maps.apigw.ntruss.com/map-direction/v1",
        alias="NAVER_DIRECTIONS_BASE_URL",
    )
    naver_geocoding_base_url: str = Field(
        default="https://maps.apigw.ntruss.com/map-geocode/v2",
        alias="NAVER_GEOCODING_BASE_URL",
    )
    aihub_data_root: str | None = Field(default=None, alias="AIHUB_DATA_ROOT")
    aihub_api_key: str | None = Field(default=None, alias="AIHUB_API_KEY")
    its_node_link_data_root: str | None = Field(default=None, alias="ITS_NODE_LINK_DATA_ROOT")
    backend_api_base_url: str | None = Field(default=None, alias="BACKEND_API_BASE_URL")
    route_data_max_age_seconds: int | None = Field(default=None, alias="ROUTE_DATA_MAX_AGE_SECONDS")
    hospital_data_max_age_seconds: int | None = Field(
        default=None,
        alias="HOSPITAL_DATA_MAX_AGE_SECONDS",
    )
    hospital_status_max_age_seconds: int | None = Field(
        default=None, alias="HOSPITAL_STATUS_MAX_AGE_SECONDS"
    )
    emergency_institution_data_max_age_seconds: int | None = Field(
        default=None,
        alias="EMERGENCY_INSTITUTION_DATA_MAX_AGE_SECONDS",
    )
    chungbuk_sido_code: str = Field(default="330000", alias="CHUNGBUK_SIDO_CODE")
    chungbuk_region_name: str = Field(default="충청북도", alias="CHUNGBUK_REGION_NAME")
    nemc_hira_coordinate_warning_meters: float = Field(
        default=1000.0,
        ge=0,
        alias="NEMC_HIRA_COORDINATE_WARNING_METERS",
    )
    candidate_radius_km: float = Field(default=10.0, ge=5.0, le=10.0, alias="CANDIDATE_RADIUS_KM")
    naver_directions_max_calls: int | None = Field(
        default=None,
        ge=1,
        alias="NAVER_DIRECTIONS_MAX_CALLS",
    )
    recommendation_route_candidate_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        alias="RECOMMENDATION_ROUTE_CANDIDATE_LIMIT",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings snapshot."""

    return Settings()
