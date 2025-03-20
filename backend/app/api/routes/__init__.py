from fastapi import APIRouter
from .costs import router as costs_router
from .metrics import router as metrics_router

router = APIRouter()

router.include_router(costs_router, prefix="/costs", tags=["costs"])
router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
