"""Provider-neutral route contracts; external response fields stay raw until verified."""

from datetime import datetime
from typing import Any

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
    path: list[tuple[float, float]] | None = None
    source_name: str
    source_record_id: str | None = None
    raw_payload_id: str | None = None
    schema_version: str
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class RouteDestination(BaseModel):
    """One source-backed hospital destination for a map route lookup."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteBatchQuery(BaseModel):
    """One patient origin and up to ten visible hospital destinations."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str | None = Field(default=None, min_length=1)
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destinations: list[RouteDestination] = Field(min_length=1, max_length=10)


class RouteBatchItem(BaseModel):
    """One successful hospital route in a batch response."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: str
    route: RouteSnapshotData


class RouteBatchError(BaseModel):
    """A destination-specific route failure without fabricated route data."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: str
    code: str
    message: str


class RouteBatchResponse(BaseModel):
    """Successful routes and explicit per-destination failures."""

    model_config = ConfigDict(extra="forbid")

    routes: list[RouteBatchItem]
    errors: list[RouteBatchError]
