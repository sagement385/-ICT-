"""Receive stage for a validated cross-team patient event."""

from app.modules.patient.schemas import PatientEventRequest


def receive(event: PatientEventRequest) -> PatientEventRequest:
    """Pass the contract object to the next stage without changing values."""

    return event

