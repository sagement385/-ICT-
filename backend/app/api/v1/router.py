"""Composition root for API v1 routers."""

from fastapi import APIRouter

from app.api.v1 import health, hospitals, locations, patients, recommendations, routing

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(patients.router)
router.include_router(hospitals.router)
router.include_router(locations.router)
router.include_router(recommendations.router)
router.include_router(routing.router)
