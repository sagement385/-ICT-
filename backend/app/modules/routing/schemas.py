"""Provider-neutral route contracts; external response fields stay raw until verified."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RouteQuery(BaseModel):
    """Coordinates for a route request."""

    model_config = ConfigDict(extra="forbid")

    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)


class RouteSnapshotData(BaseModel):
    """Normalized route data after a verified provider parser exists."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str
    distance_meters: int = Field(ge=0)
    duration_seconds: int = Field(ge=0)
    traffic_summary: str | None = None
    fetched_at: datetime

