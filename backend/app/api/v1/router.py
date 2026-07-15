"""Composition root for API v1 routers."""

from fastapi import APIRouter

from app.api.v1 import health, hospitals, patients, recommendations

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(patients.router)
router.include_router(hospitals.router)
router.include_router(recommendations.router)

