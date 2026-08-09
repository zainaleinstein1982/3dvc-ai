from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_admin
from app.observability.metrics import metrics
from app.ai.distributed_queue import distributed_queue
from app.storage.object_storage import object_storage

router = APIRouter()

@router.get("/live")
async def liveness():
    return {"status": "alive"}

@router.get("/ready")
async def readiness(user: dict = Depends(get_current_user)):
    return {"status": "ready", "tenant": user["tenantId"]}

@router.get("/admin-diagnostics")
async def admin_diagnostics(user: dict = Depends(require_admin)):
    return {
        "status": "ready",
        "dependencies": {
            "redis": "healthy" if distributed_queue.is_available() else "unavailable",
            "minio": "healthy" if object_storage.is_available else "unavailable",
            "gpu_workers": distributed_queue.get_worker_stats().get("total", 0) if distributed_queue.is_available() else 0
        },
        "metrics": metrics.snapshot()
    }
