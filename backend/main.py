from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, health, rooms, ai, sfu, sfu_webhook
from app.db.database import init_db
from app.observability.metrics import metrics
from app.ai.gpu_manager import gpu_manager

app = FastAPI(title="3DVC AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://3dvc.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(sfu.router, prefix="/api/sfu", tags=["sfu"])
app.include_router(sfu_webhook.router, prefix="/api", tags=["sfu"])

@app.on_event("startup")
async def startup_event():
    await init_db()
    await gpu_manager.start()

@app.get("/")
async def root(): return {"status": "online", "docs": "/docs"}
