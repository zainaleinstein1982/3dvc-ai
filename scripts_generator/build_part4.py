import os

FILES = {
    "3dvc/backend/requirements.txt": """fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy[asyncio]==2.0.31
asyncpg==0.29.0
passlib[bcrypt]==1.7.4
pyjwt==2.9.0
slowapi==0.1.9
redis==5.0.7
minio==7.2.7
livekit-api==0.7.0
openai==1.35.7
alembic==1.13.2
pydantic-settings==2.4.0
python-dotenv==1.0.1
""",
    "3dvc/backend/main.py": """from fastapi import FastAPI
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
""",
    "3dvc/backend/app/db/database.py": """from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://threedvc:devpassword@localhost:5432/threedvc_db")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from app.db import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    from app.auth.security import hash_password
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(models.User).filter_by(email="admin@3dvc.ai"))
        if not result.scalars().first():
            admin_tenant = models.Tenant(name="Admin Tenant", slug="admin")
            session.add(admin_tenant)
            await session.flush()
            admin_user = models.User(
                tenant_id=admin_tenant.id,
                email="admin@3dvc.ai",
                display_name="Administrator",
                password_hash=hash_password("admin123"),
                role="ADMIN",
                status="ACTIVE"
            )
            session.add(admin_user)
            await session.commit()
""",
    "3dvc/backend/app/db/models.py": """import uuid
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="USER")
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RoomMember(Base):
    __tablename__ = "room_members"
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(String, default="PARTICIPANT")
    presence = Column(String, default="OFFLINE")
    is_muted = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    refresh_token_hash = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, default=datetime.datetime.utcnow)
""",
    "3dvc/backend/app/auth/security.py": """from passlib.context import CryptContext
import jwt
import os
import secrets
import hashlib
import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)))
    to_encode.update({"exp": expire, "iat": datetime.datetime.utcnow(), "iss": "3dvc-ai", "aud": "3dvc-client"})
    return jwt.encode(to_encode, os.getenv("JWT_SECRET"), algorithm="HS256")

def generate_refresh_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash

def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
""",
    "3dvc/backend/app/auth/dependencies.py": """from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import os
from app.db.database import get_db
from app.db import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> dict:
    credentials_exception = HTTPException(status_code=401, detail="Invalid credentials")
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"], issuer="3dvc-ai", audience="3dvc-client", options={"require": ["exp", "iat", "iss", "aud", "sub"]})
        user_id = payload.get("sub")
        if user_id is None: raise credentials_exception
    except jwt.PyJWTError: raise credentials_exception
    
    user = await db.get(models.User, user_id)
    if not user or user.status != "ACTIVE": raise HTTPException(status_code=403, detail="Inactive or invalid user")
    
    return {
        "userId": str(user.id),
        "tenantId": str(user.tenant_id),
        "role": user.role,
        "email": user.email
    }

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] not in ["ADMIN", "MODERATOR"]:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
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
