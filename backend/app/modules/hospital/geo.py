"""Coordinate calculations used by source-backed hospital candidate lookup."""

from math import atan2, cos, radians, sin, sqrt


def distance_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    """Return the great-circle distance between two WGS84 coordinate pairs."""

    earth_radius_km = 6371.0088
    delta_latitude = radians(latitude_b - latitude_a)
    delta_longitude = radians(longitude_b - longitude_a)
    haversine = (
        sin(delta_latitude / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(delta_longitude / 2) ** 2
    )
    return earth_radius_km * 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
