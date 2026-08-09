from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://threedvc:devpassword@localhost:5432/threedvc_db")

# Konversi otomatis skema postgresql:// ke postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

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