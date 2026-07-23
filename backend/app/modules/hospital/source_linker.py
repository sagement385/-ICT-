"""Conservative cross-source hospital identity matching utilities."""

import re
from dataclasses import dataclass

from app.integrations.nemc.schemas import NemcEmergencyInstitutionRecord
from app.modules.hospital.geo import distance_km
from app.modules.hospital.models import Hospital


@dataclass(frozen=True)
class EmergencyInstitutionMatch:
    """One unambiguous source match with coordinate quality metadata."""

    hospital: Hospital | None
    status: str
    coordinate_distance_meters: float | None
    coordinate_warning: bool


def normalize_institution_name(value: str) -> str:
    """Normalize spacing and punctuation without applying fuzzy substitutions."""

    return re.sub(r"[^0-9\uac00-\ud7a3A-Za-z]", "", value).lower()


def match_emergency_institution(
    record: NemcEmergencyInstitutionRecord,
    hospitals: list[Hospital],
    coordinate_warning_meters: float,
) -> EmergencyInstitutionMatch:
    """Accept only one exact normalized-name match and audit coordinate disagreement."""

    normalized_name = normalize_institution_name(record.institution_name)
    matches = [
        hospital
        for hospital in hospitals
        if normalize_institution_name(hospital.hospital_name) == normalized_name
    ]
    if not matches:
        return EmergencyInstitutionMatch(None, "unmatched", None, True)
    if len(matches) != 1:
        return EmergencyInstitutionMatch(None, "ambiguous", None, True)

    hospital = matches[0]
    coordinate_distance_meters: float | None = None
    if (
        record.latitude is not None
        and record.longitude is not None
        and hospital.latitude is not None
        and hospital.longitude is not None
    ):
        coordinate_distance_meters = (
            distance_km(
                record.latitude,
                record.longitude,
                hospital.latitude,
                hospital.longitude,
            )
            * 1000
        )
    return EmergencyInstitutionMatch(
        hospital=hospital,
        status="matched",
        coordinate_distance_meters=coordinate_distance_meters,
        coordinate_warning=(
            coordinate_distance_meters is None
            or coordinate_distance_meters > coordinate_warning_meters
        ),
    )
