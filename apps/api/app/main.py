from fastapi import FastAPI

from app.api.v1.dataset_snapshots import router as dataset_snapshots_router
from app.api.v1.dataset import router as dataset_router
from app.api.v1.annotations import router as annotations_router
from app.api.v1.auth import router as auth_router

from app.api.v1.health import router as health_router
from app.api.v1.studies import router as studies_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.models import router as models_router
from app.api.v1.audit import router as audit_router
from app.api.v1.results import router as results_router
from app.api.v1.operations import router as operations_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="BoneQC API",
    description="Backend API for BoneQC densitometry quality-control platform.",
    version=settings.version,
)

app.include_router(dataset_snapshots_router, prefix="/api/v1")
app.include_router(dataset_router, prefix="/api/v1")
app.include_router(annotations_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")
app.include_router(studies_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(results_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {
        "service": settings.service_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }
