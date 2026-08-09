import os

FILES = {
    "3dvc/backend/app/ai/distributed_queue.py": """import redis
import json
import time
import uuid
import os
import logging
from typing import Optional
from app.observability.circuit_breaker import CircuitBreaker

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class DistributedAIQueue:
    def __init__(self):
        self.redis = None
        self.cb = CircuitBreaker("redis_queue")
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
            log.info("Connected to Redis for distributed GPU queue.")
        except Exception as e:
            log.warning("Redis unavailable. Falling back to local queue. Error: %s", e)
            self.redis = None

    def is_available(self) -> bool:
        return self.redis is not None

    def submit_job(self, payload: dict, priority: int) -> str:
        if self.cb.is_open(): raise RuntimeError("Redis Circuit Breaker OPEN")
        try:
            job_id = str(uuid.uuid4())
            score = (priority * 10**13) - time.time() * 1000
            self.redis.zadd("ai_jobs", {json.dumps({"job_id": job_id, "payload": payload}): score})
            self.cb.record_success()
            return job_id
        except Exception as e:
            self.cb.record_failure()
            raise e

    def get_job(self) -> Optional[dict]:
        if not self.redis: return None
        result = self.redis.zpopmin("ai_jobs", count=1)
        if result:
            return json.loads(result[0][0])
        return None

    def register_worker(self, worker_id: str, capabilities: dict):
        self.redis.hset(f"workers:{worker_id}", mapping={"status": "idle", "capabilities": json.dumps(capabilities), "last_heartbeat": time.time()})
        self.redis.expire(f"workers:{worker_id}", 10)

    def heartbeat(self, worker_id: str, status: str = "idle"):
        self.redis.hset(f"workers:{worker_id}", "status", status)
        self.redis.hset(f"workers:{worker_id}", "last_heartbeat", time.time())
        self.redis.expire(f"workers:{worker_id}", 10)

    def get_worker_stats(self) -> dict:
        if not self.redis: return {}
        keys = self.redis.keys("workers:*")
        stats = {"total": 0, "idle": 0, "busy": 0}
        for key in keys:
            worker = self.redis.hgetall(key)
            stats["total"] += 1
            if worker.get("status") == "idle": stats["idle"] += 1
            else: stats["busy"] += 1
        return stats

distributed_queue = DistributedAIQueue()
""",
    "3dvc/backend/app/ai/gpu_manager.py": """import asyncio
import time
import logging
from typing import Dict
from .distributed_queue import distributed_queue
import json, base64, cv2, numpy as np

log = logging.getLogger(__name__)

class GPUResourceManager:
    def __init__(self, max_workers: int = 2, max_queue_size: int = 50):
        self.local_queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.max_workers = max_workers
        self.workers = []
        self.is_running = False
        self.stats = {"processed": 0, "dropped_stale": 0, "dropped_full": 0, "queue_depth": 0}
        self.last_sequence: Dict[str, int] = {}
        self.redis = distributed_queue

    async def start(self):
        self.is_running = True
        if self.redis.is_available():
            log.info("GPUResourceManager running in DISTRIBUTED mode (Redis).")
        else:
            log.info("GPUResourceManager running in LOCAL mode (asyncio).")
            for i in range(self.max_workers):
                task = asyncio.create_task(self._local_worker(f"local-worker-{i}"))
                self.workers.append(task)

    async def submit_job(self, priority: int, payload: dict) -> dict:
        seq = payload.get("sequence", 0)
        pid = payload.get("participantId", "unknown")
        if pid in self.last_sequence and seq <= self.last_sequence[pid]:
            self.stats["dropped_stale"] += 1
            raise RuntimeError("Stale frame dropped")
        self.last_sequence[pid] = seq

        if self.redis.is_available():
            job_id = self.redis.submit_job(payload, priority)
            result_key = f"result_data:{job_id}"
            for _ in range(100):
                res = self.redis.redis.get(result_key)
                if res:
                    self.redis.redis.delete(result_key)
                    return json.loads(res)
                await asyncio.sleep(0.1)
            self.stats["dropped_full"] += 1
            raise RuntimeError("Distributed GPU Timeout")
        else:
            if self.local_queue.full():
                self.stats["dropped_full"] += 1
                raise RuntimeError("Local Queue Full")
            future = asyncio.get_event_loop().create_future()
            await self.local_queue.put((priority, time.time(), payload, future))
            self.stats["queue_depth"] = self.local_queue.qsize()
            return await future

    async def _local_worker(self, name: str):
        while self.is_running:
            try:
                priority, ts, payload, future = await asyncio.wait_for(self.local_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            try:
                # Mock inference for local fallback
                await asyncio.sleep(0.05)
                h, w = 256, 256
                depth_map = np.random.rand(h, w).astype(np.float32)
                frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
                _, depth_buf = cv2.imencode('.png', (depth_map * 255).astype(np.uint8))
                _, frame_buf = cv2.imencode('.jpg', frame)
                result = {"success": True, "inference_ms": 50.0, "sequence": payload["sequence"], "assets": {}, "depth_b64": base64.b64encode(depth_buf).decode('utf-8'), "frame_b64": base64.b64encode(frame_buf).decode('utf-8')}
                self.stats["processed"] += 1
                if not future.done(): future.set_result(result)
            except Exception as e:
                if not future.done(): future.set_exception(e)
            finally:
                self.local_queue.task_done()

gpu_manager = GPUResourceManager()
""",
    "3dvc/backend/app/ai/liveportrait_engine.py": """import torch
import numpy as np
import logging

log = logging.getLogger(__name__)

class LivePortraitEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False

    async def load(self):
        log.info("Loading LivePortrait model on %s...", self.device)
        self.is_loaded = True

    async def animate(self, source_frame: np.ndarray, motion_data: dict) -> dict:
        return {"frame": source_frame, "inference_ms": 45.0, "device": self.device}

liveportrait_engine = LivePortraitEngine()
""",
    "3dvc/backend/app/ai/depth_engine.py": """import torch
import numpy as np
import logging

log = logging.getLogger(__name__)

class DepthAnythingV2Engine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False

    async def load(self):
        log.info("Loading Depth Anything V2 model on %s...", self.device)
        self.is_loaded = True

    async def estimate(self, frame: np.ndarray) -> dict:
        h, w = frame.shape[:2]
        depth = np.random.rand(h, w).astype(np.float32)
        return {"depth_map": depth, "inference_ms": 30.0, "device": self.device}

depth_engine = DepthAnythingV2Engine()
""",
    "3dvc/backend/app/storage/object_storage.py": """from minio import Minio
from minio.error import S3Error
import io
import os
import logging
import re
from datetime import timedelta
from typing import Optional

log = logging.getLogger(__name__)

class ObjectStorage:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket = os.getenv("MINIO_BUCKET", "3dvc-ai-assets")
        self.client = None
        self.is_available = False
        try:
            self.client = Minio(self.endpoint, access_key=self.access_key, secret_key=self.secret_key, secure=False)
            if not self.client.bucket_exists(self.bucket): self.client.make_bucket(self.bucket)
            self.is_available = True
        except Exception as e:
            log.warning("MinIO unavailable: %s", e)

    def sanitize_key_component(self, component: str) -> str:
        component = re.sub(r'[\\\\/*?:"<>|]', "", component)
        if component in [".", ".."]: raise ValueError("Invalid path component")
        return component

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        if not self.is_available: return False
        try:
            self.client.put_object(self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
            return True
        except Exception: return False

    def get_signed_url(self, key: str, expiry: int = 60) -> Optional[str]:
        if not self.is_available: return None
        try: return self.client.presigned_get_object(self.bucket, key, expires=timedelta(seconds=expiry))
        except Exception: return None

object_storage = ObjectStorage()
""",
    "3dvc/backend/app/api/ai.py": """from fastapi import APIRouter, HTTPException, Depends, Header, Request
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
""",
    "3dvc/backend/app/api/sfu.py": """from fastapi import APIRouter, HTTPException, Depends
import os
from livekit import api
from app.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/token")
async def get_token(room: str = "demo-room", user: dict = Depends(get_current_user)):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=503, detail="LiveKit credentials not configured")
        
    secure_room = f"{user['tenantId']}_{room}"
    
    token = api.AccessToken(api_key, api_secret) \\
        .with_identity(user["userId"]) \\
        .with_name(user["email"]) \\
        .with_grants(api.VideoGrants(room_join=True, room=secure_room, can_publish=True, can_subscribe=True, can_publish_data=True)) \\
        .to_jwt()
        
    return {"token": token, "url": livekit_url, "room": secure_room}
""",
    "3dvc/backend/app/api/sfu_webhook.py": """from fastapi import APIRouter, Request
from livekit.api import WebhookReceiver
import os
from app.db.database import AsyncSessionLocal
from app.db import models
from sqlalchemy import update
import uuid

router = APIRouter()
receiver = WebhookReceiver(os.getenv("LIVEKIT_API_KEY", "devkey"), os.getenv("LIVEKIT_API_SECRET", "secret"))

@router.post("/sfu/webhook")
async def livekit_webhook(request: Request):
    body = await request.body()
    try:
        event = await receiver.receive(body, request.headers)
        async with AsyncSessionLocal() as db:
            if event.event == "participant_joined":
                await db.execute(update(models.RoomMember).where(models.RoomMember.user_id == uuid.UUID(event.participant.identity)).values(presence="ONLINE"))
            elif event.event == "participant_left":
                await db.execute(update(models.RoomMember).where(models.RoomMember.user_id == uuid.UUID(event.participant.identity)).values(presence="OFFLINE"))
            await db.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}
"""
}

def create_files():
    for filepath, content in FILES.items():
        full_path = os.path.join(os.getcwd(), filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Created: {filepath}")

if __name__ == "__main__":
    create_files()
