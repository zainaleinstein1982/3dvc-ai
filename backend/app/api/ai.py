from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user
from app.ai.gpu_manager import gpu_manager
from app.observability.metrics import metrics
from slowapi import Limiter
from slowapi.util import get_remote_address
import time, uuid

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class MotionData(BaseModel):
    yaw: float = Field(..., ge=-180, le=180)
    pitch: float = Field(..., ge=-180, le=180)
    roll: float = Field(..., ge=-180, le=180)
    eyeX: float = Field(..., ge=-1, le=1)
    eyeY: float = Field(..., ge=-1, le=1)

class AIPayload(BaseModel):
    image_b64: str = Field(..., max_length=1024 * 1024)
    motion: MotionData
    sequence: int = Field(..., ge=0)
    timestamp: float
    priority: int = 3
    edge_tracking_active: bool = False

@router.post("/process")
@limiter.limit("30/minute")
async def process_frame(request: Request, payload: AIPayload, user: dict = Depends(get_current_user), x_request_id: str = Header(None)):
    request_id = x_request_id or str(uuid.uuid4())
    start_time = time.time()
    
    if payload.edge_tracking_active and payload.sequence % 5 != 0:
        metrics.increment("gpu_jobs_avoided")
        raise HTTPException(status_code=429, detail="Edge tracking active. Backend job skipped.")

    job_payload = {"participantId": user["userId"], "sequence": payload.sequence, "timestamp": payload.timestamp, "requestId": request_id}
    
    try:
        result = await gpu_manager.submit_job(payload.priority, job_payload)
        latency = (time.time() - start_time) * 1000
        metrics.record_latency("ai_pipeline", latency)
        metrics.increment("jobs_completed")
        return {"status": "success", "data": result}
    except RuntimeError as e:
        metrics.increment("jobs_failed")
        raise HTTPException(status_code=429, detail=str(e))
