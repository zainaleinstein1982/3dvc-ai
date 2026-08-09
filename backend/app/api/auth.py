from fastapi import APIRouter, Depends, HTTPException, Response, Request
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
async def login(request: Request, response: Response, credentials: LoginReq, db: AsyncSession = Depends(get_db)):
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
