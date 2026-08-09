import os

FILES = {
    "3dvc/backend/app/observability/metrics.py": """import time
from collections import defaultdict
import threading

class MetricsAggregator:
    def __init__(self):
        self.lock = threading.Lock()
        self.counters = defaultdict(int)
        self.latencies = defaultdict(list)
        
    def increment(self, name: str, value: int = 1):
        with self.lock:
            self.counters[name] += value
            
    def record_latency(self, name: str, ms: float):
        with self.lock:
            self.latencies[name].append(ms)
            if len(self.latencies[name]) > 1000:
                self.latencies[name] = self.latencies[name][-500:]
                
    def get_percentile(self, name: str, p: float) -> float:
        with self.lock:
            data = sorted(self.latencies.get(name, []))
            if not data: return 0
            idx = int(len(data) * p)
            return data[min(idx, len(data)-1)]
            
    def snapshot(self) -> dict:
        with self.lock:
            return {
                "counters": dict(self.counters),
                "latencies_ms": {
                    "ai_pipeline": {
                        "p50": self.get_percentile("ai_pipeline", 0.5),
                        "p95": self.get_percentile("ai_pipeline", 0.95),
                        "p99": self.get_percentile("ai_pipeline", 0.99)
                    }
                }
            }

metrics = MetricsAggregator()
""",
    "3dvc/backend/app/observability/circuit_breaker.py": """import time
import logging

log = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_time: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time = 0

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            log.warning("Circuit breaker %s tripped OPEN", self.name)

    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF_OPEN"
                log.info("Circuit breaker %s entering HALF_OPEN", self.name)
                return False
            return True
        return False
""",
    "3dvc/backend/app/api/health.py": """from fastapi import APIRouter, Depends
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
""",
    "3dvc/backend/app/api/auth.py": """from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.db import models
from app.auth.security import verify_password, create_access_token, generate_refresh_token, hash_string
from app.auth.dependencies import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address
import datetime

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class LoginReq(BaseModel):
    email: str
    password: str

@router.post("/login")
@limiter.limit("5/minute")
async def login(req: Request, response: Response, credentials: LoginReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).filter_by(email=credentials.email))
    user = result.scalars().first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token = create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role})
    raw_refresh, hash_refresh = generate_refresh_token()
    
    session = models.Session(
        user_id=user.id, tenant_id=user.tenant_id,
        refresh_token_hash=hash_refresh,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(session)
    await db.commit()
    
    response.set_cookie(key="refresh_token", value=raw_refresh, httponly=True, samesite="strict", secure=False)
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": str(user.id), "email": user.email, "role": user.role}}

@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    token_hash = hash_string(refresh_token)
    result = await db.execute(select(models.Session).filter_by(refresh_token_hash=token_hash, revoked_at=None))
    session = result.scalars().first()
    
    if not session or session.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    session.revoked_at = datetime.datetime.utcnow()
    new_raw, new_hash = generate_refresh_token()
    new_session = models.Session(
        user_id=session.user_id, tenant_id=session.tenant_id,
        refresh_token_hash=new_hash,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(new_session)
    await db.commit()
    
    response.set_cookie(key="refresh_token", value=new_raw, httponly=True, samesite="strict")
    user = await db.get(models.User, session.user_id)
    access_token = create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db), refresh_token: str = None):
    if refresh_token:
        token_hash = hash_string(refresh_token)
        await db.execute(update(models.Session).where(models.Session.refresh_token_hash == token_hash).values(revoked_at=datetime.datetime.utcnow()))
        await db.commit()
    response.delete_cookie("refresh_token")
    return {"status": "logged_out"}

@router.post("/logout-all")
async def logout_all(response: Response, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(models.Session).where(models.Session.user_id == user["userId"]).values(revoked_at=datetime.datetime.utcnow()))
    await db.commit()
    response.delete_cookie("refresh_token")
    return {"status": "all_sessions_revoked"}

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
""",
    "3dvc/backend/app/api/rooms.py": """from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.db import models
from app.auth.dependencies import get_current_user
import uuid

router = APIRouter()

class RoomCreate(BaseModel):
    name: str

@router.post("")
async def create_room(req: RoomCreate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    room = models.Room(tenant_id=uuid.UUID(user["tenantId"]), name=req.name, owner_id=uuid.UUID(user["userId"]))
    db.add(room)
    await db.flush()
    member = models.RoomMember(room_id=room.id, user_id=uuid.UUID(user["userId"]), role="OWNER", presence="OFFLINE", is_approved=True)
    db.add(member)
    await db.commit()
    return {"roomId": str(room.id), "name": room.name}

@router.get("")
async def list_rooms(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Room).filter_by(tenant_id=uuid.UUID(user["tenantId"]), status="ACTIVE"))
    return [{"id": str(r.id), "name": r.name} for r in result.scalars().all()]

@router.get("/{room_id}/members")
async def get_members(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User, models.RoomMember).join(models.RoomMember, models.User.id == models.RoomMember.user_id).filter(models.RoomMember.room_id == uuid.UUID(room_id)))
    members = []
    for u, m in result.all():
        members.append({"userId": str(u.id), "displayName": u.display_name, "role": m.role, "presence": m.presence, "is_muted": m.is_muted, "is_approved": m.is_approved})
    return members

@router.post("/{room_id}/join")
async def join_room(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    room = await db.get(models.Room, uuid.UUID(room_id))
    if not room or room.status != "ACTIVE": raise HTTPException(404, "Room not found or ended")
    if room.tenant_id != uuid.UUID(user["tenantId"]): raise HTTPException(403, "Cross-tenant access denied")

    result = await db.execute(select(models.RoomMember).filter_by(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"])))
    member = result.scalars().first()
    if not member:
        member = models.RoomMember(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"]), role="PARTICIPANT", presence="ONLINE", is_approved=user["role"] in ["ADMIN", "MODERATOR"])
        db.add(member)
    else:
        member.presence = "ONLINE"
    await db.commit()
    if not member.is_approved: raise HTTPException(403, "Waiting for moderator approval")
    return {"status": "joined", "roomId": room_id}

@router.post("/{room_id}/leave")
async def leave_room(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(models.RoomMember).where(models.RoomMember.room_id == uuid.UUID(room_id), models.RoomMember.user_id == uuid.UUID(user["userId"])).values(presence="OFFLINE"))
    await db.commit()
    return {"status": "left"}

@router.post("/{room_id}/kick/{target_id}")
async def kick_user(room_id: str, target_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.RoomMember).filter_by(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"])))
    actor = result.scalars().first()
    if not actor or actor.role not in ["OWNER", "MODERATOR"]: raise HTTPException(403, "Insufficient privileges")
    await db.execute(update(models.RoomMember).where(models.RoomMember.room_id == uuid.UUID(room_id), models.RoomMember.user_id == uuid.UUID(target_id)).values(presence="OFFLINE", is_approved=False))
    await db.commit()
    return {"status": "kicked"}

@router.post("/{room_id}/end")
async def end_room(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.RoomMember).filter_by(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"])))
    actor = result.scalars().first()
    if not actor or actor.role != "OWNER": raise HTTPException(403, "Only owner can end room")
    room = await db.get(models.Room, uuid.UUID(room_id))
    room.status = "ENDED"
    await db.execute(update(models.RoomMember).where(models.RoomMember.room_id == uuid.UUID(room_id)).values(presence="OFFLINE"))
    await db.commit()
    return {"status": "ended"}
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
